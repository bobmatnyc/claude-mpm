---
name: github-actions
description: "GitHub Actions CI/CD workflows for automating build, test, and deployment"
version: 1.0.0
progressive_disclosure:
  entry_point:
    - summary
    - when_to_use
    - quick_start
  tokens:
    entry: 70
    full: 5000
---

# GitHub Actions CI/CD

## Summary
GitHub Actions is GitHub's native CI/CD platform for automating software workflows. Define workflows in YAML files to build, test, and deploy code directly from your repository with event-driven automation.

## When to Use
- Automate testing on every pull request
- Build and deploy applications on merge to main
- Schedule regular tasks (nightly builds, backups)
- Publish packages to registries (npm, PyPI, Docker Hub)
- Run security scans and code quality checks
- Automate release processes and changelog generation

## Quick Start

### Basic Test Workflow
Create `.github/workflows/test.yml`:

```yaml
name: Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test
```

---

# Complete GitHub Actions Guide

## Core Concepts

### Workflows
YAML files in `.github/workflows/` that define automation pipelines.

**Structure**:
- **Name**: Workflow identifier
- **Triggers**: Events that start the workflow
- **Jobs**: One or more jobs to execute
- **Steps**: Commands/actions within each job

```yaml
name: CI Pipeline
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Building project"
```

### Jobs
Independent execution units that run in parallel by default.

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: npm run lint

  test:
    runs-on: ubuntu-latest
    needs: lint  # Wait for lint to complete
    steps:
      - run: npm test

  deploy:
    runs-on: ubuntu-latest
    needs: [lint, test]  # Wait for both
    steps:
      - run: ./deploy.sh
```

### Steps
Sequential commands or actions within a job.

```yaml
steps:
  # Use pre-built action
  - uses: actions/checkout@v4

  # Run shell command
  - run: npm install

  # Named step with environment
  - name: Run tests
    run: npm test
    env:
      NODE_ENV: test
```

### Actions
Reusable units of code (from marketplace or custom).

```yaml
# Official action
- uses: actions/checkout@v4

# Third-party action
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: user/app:latest

# Local action
- uses: ./.github/actions/custom-action
```

## Workflow Syntax

### Triggers (on)

#### Push Events
```yaml
on:
  push:
    branches:
      - main
      - 'releases/**'  # Wildcard pattern
    tags:
      - 'v*'  # All version tags
    paths:
      - 'src/**'
      - '!src/docs/**'  # Exclude docs
```

#### Pull Request Events
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main, develop]
    paths-ignore:
      - '**.md'
      - 'docs/**'
```

#### Schedule (Cron)
```yaml
on:
  schedule:
    # Every day at 2:30 AM UTC
    - cron: '30 2 * * *'
    # Every Monday at 9:00 AM UTC
    - cron: '0 9 * * 1'
```

#### Manual Trigger
```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        type: choice
        options:
          - staging
          - production
      version:
        description: 'Version to deploy'
        required: false
        default: 'latest'
```

#### Multiple Triggers
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:  # Manual
```

### Environment Variables

#### Workflow-level
```yaml
env:
  NODE_ENV: production
  API_URL: https://api.example.com

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo $NODE_ENV
```

#### Job-level
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      TEST_DATABASE: test_db
    steps:
      - run: pytest
```

#### Step-level
```yaml
steps:
  - name: Build
    run: npm run build
    env:
      BUILD_TARGET: production
```

### Secrets
Store sensitive data in repository settings.

```yaml
steps:
  - name: Deploy
    run: ./deploy.sh
    env:
      API_KEY: ${{ secrets.API_KEY }}
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

**Best Practices**:
- Never commit secrets to code
- Use GitHub encrypted secrets
- Limit secret access to specific environments
- Rotate secrets regularly

## Contexts

### github Context
Repository and workflow information.

```yaml
steps:
  - name: Print context
    run: |
      echo "Repository: ${{ github.repository }}"
      echo "Ref: ${{ github.ref }}"
      echo "SHA: ${{ github.sha }}"
      echo "Actor: ${{ github.actor }}"
      echo "Event: ${{ github.event_name }}"
      echo "Branch: ${{ github.ref_name }}"
```

### env Context
Access environment variables.

```yaml
env:
  BUILD_ID: 12345

steps:
  - run: echo "Build ${{ env.BUILD_ID }}"
```

### secrets Context
Access repository secrets.

```yaml
- run: echo "Token exists"
  env:
    TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### matrix Context
Access matrix values.

```yaml
strategy:
  matrix:
    node: [18, 20, 22]
steps:
  - run: echo "Testing Node ${{ matrix.node }}"
```

### needs Context
Access outputs from dependent jobs.

```yaml
jobs:
  build:
    outputs:
      version: ${{ steps.get_version.outputs.version }}
    steps:
      - id: get_version
        run: echo "version=1.2.3" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    steps:
      - run: echo "Deploying ${{ needs.build.outputs.version }}"
```

## Runners

### GitHub-hosted Runners

```yaml
jobs:
  ubuntu:
    runs-on: ubuntu-latest  # ubuntu-22.04

  macos:
    runs-on: macos-latest  # macOS 14

  windows:
    runs-on: windows-latest  # Windows 2022

  specific:
    runs-on: ubuntu-20.04  # Specific version
```

**Available Runners**:
- `ubuntu-latest`, `ubuntu-22.04`, `ubuntu-20.04`
- `macos-latest`, `macos-14`, `macos-13`
- `windows-latest`, `windows-2022`, `windows-2019`

### Self-hosted Runners

```yaml
runs-on: self-hosted

# With labels
runs-on: [self-hosted, linux, x64, gpu]
```

**Setup**:
1. Go to Settings → Actions → Runners
2. Click "New self-hosted runner"
3. Follow platform-specific instructions
4. Add custom labels for targeting

## Matrix Strategies

### Basic Matrix
Test across multiple versions.

```yaml
strategy:
  matrix:
    node: [18, 20, 22]
    os: [ubuntu-latest, macos-latest, windows-latest]

runs-on: ${{ matrix.os }}
steps:
  - uses: actions/setup-node@v4
    with:
      node-version: ${{ matrix.node }}
```

### Include/Exclude

```yaml
strategy:
  matrix:
    node: [18, 20, 22]
    os: [ubuntu-latest, windows-latest]
    include:
      # Add specific combination
      - node: 22
        os: macos-latest
        experimental: true
    exclude:
      # Remove specific combination
      - node: 18
        os: windows-latest
```

### Fail-fast

```yaml
strategy:
  fail-fast: false  # Continue other jobs if one fails
  matrix:
    node: [18, 20, 22]
```

### Max Parallel

```yaml
strategy:
  max-parallel: 2  # Run only 2 jobs concurrently
  matrix:
    node: [18, 20, 22]
```

## Common Actions

### Checkout Code
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Full history for changelog
    submodules: true  # Include submodules
```

### Setup Node.js
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'  # or 'yarn', 'pnpm'
    registry-url: 'https://registry.npmjs.org'
```

### Setup Python
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'
```

### Setup Java
```yaml
- uses: actions/setup-java@v4
  with:
    distribution: 'temurin'
    java-version: '17'
    cache: 'maven'
```

### Setup Go
```yaml
- uses: actions/setup-go@v5
  with:
    go-version: '1.21'
    cache: true
```

### Cache Dependencies
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

### Upload Artifacts
```yaml
- uses: actions/upload-artifact@v4
  with:
    name: build-output
    path: dist/
    retention-days: 7
```

### Download Artifacts
```yaml
- uses: actions/download-artifact@v4
  with:
    name: build-output
    path: dist/
```

## Conditional Execution

### if Conditions
```yaml
steps:
  - name: Deploy to production
    if: github.ref == 'refs/heads/main'
    run: ./deploy.sh

  - name: Deploy to staging
    if: github.ref == 'refs/heads/develop'
    run: ./deploy-staging.sh

  - name: Only on PR
    if: github.event_name == 'pull_request'
    run: echo "This is a PR"

  - name: On success
    if: success()
    run: echo "Previous steps succeeded"

  - name: On failure
    if: failure()
    run: echo "A step failed"

  - name: Always run
    if: always()
    run: echo "Cleanup tasks"
```

### Job Conditions
```yaml
jobs:
  deploy:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh
```

## Framework-Specific Workflows

### Node.js/TypeScript

```yaml
name: Node.js CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - run: npm ci

      - run: npm run lint

      - run: npm run type-check

      - run: npm test
        env:
          CI: true

      - run: npm run build

      - uses: codecov/codecov-action@v4
        if: matrix.node-version == 20
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
```

### Python

```yaml
name: Python CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - run: pip install -r requirements.txt

      - run: pip install pytest pytest-cov mypy ruff

      - run: ruff check .

      - run: mypy .

      - run: pytest --cov=. --cov-report=xml

      - uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.11'
```

### Docker

```yaml
name: Docker Build

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: user/app
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Next.js with Vercel

```yaml
name: Next.js CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - run: npm run lint

      - run: npm run build

      - run: npm test

  deploy-preview:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4

      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}

  deploy-production:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4

      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
```

## Deployment Patterns

### Vercel Deployment

```yaml
name: Deploy to Vercel

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
```

### Netlify Deployment

```yaml
name: Deploy to Netlify

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - run: npm ci
      - run: npm run build

      - uses: netlify/actions/cli@master
        with:
          args: deploy --prod --dir=dist
        env:
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
```

### AWS S3 + CloudFront

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - run: npm ci
      - run: npm run build

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - run: aws s3 sync dist/ s3://${{ secrets.S3_BUCKET }} --delete

      - run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

### Docker Registry Push

```yaml
name: Publish Docker Image

on:
  release:
    types: [published]

jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.event.release.tag_name }}
```

## Testing Workflows

### Unit Tests with Coverage

```yaml
name: Test Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - run: npm test -- --coverage

      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage/coverage-final.json
          fail_ci_if_error: true
```

### Integration Tests

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - run: npm ci

      - run: npm run test:integration
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
          REDIS_URL: redis://localhost:6379
```

### E2E Tests with Playwright

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - run: npx playwright install --with-deps

      - run: npm run build

      - run: npm run test:e2e

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30
```

## Release Automation

### Semantic Release

```yaml
name: Release

on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for changelog

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - run: npm ci

      - run: npx semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Create Release with Changelog

```yaml
name: Create Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Generate changelog
        id: changelog
        run: |
          # Generate changelog from commits
          CHANGELOG=$(git log $(git describe --tags --abbrev=0 HEAD^)..HEAD --pretty=format:"- %s (%h)" --no-merges)
          echo "changelog<<EOF" >> $GITHUB_OUTPUT
          echo "$CHANGELOG" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      - uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref_name }}
          release_name: Release ${{ github.ref_name }}
          body: |
            ## Changes
            ${{ steps.changelog.outputs.changelog }}
          draft: false
          prerelease: false
```

### Publish npm Package

```yaml
name: Publish to npm

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'

      - run: npm ci

      - run: npm test

      - run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

## Security Scanning

### CodeQL Analysis

```yaml
name: CodeQL

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 1'  # Weekly

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write

    strategy:
      fail-fast: false
      matrix:
        language: ['javascript', 'python']

    steps:
      - uses: actions/checkout@v4

      - uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}

      - uses: github/codeql-action/autobuild@v3

      - uses: github/codeql-action/analyze@v3
```

### Dependency Scanning

```yaml
name: Dependency Check

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 1'

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - run: npm audit --audit-level=moderate

      - run: npx snyk test
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        continue-on-error: true
```

### Trivy Container Scan

```yaml
name: Container Security Scan

on:
  push:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - run: docker build -t myapp:${{ github.sha }} .

      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

## Composite Actions

Create reusable actions in `.github/actions/`.

### Simple Composite Action

`.github/actions/setup-project/action.yml`:
```yaml
name: 'Setup Project'
description: 'Install dependencies and cache'

inputs:
  node-version:
    description: 'Node.js version'
    required: false
    default: '20'

runs:
  using: 'composite'
  steps:
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'

    - run: npm ci
      shell: bash
```

**Usage**:
```yaml
steps:
  - uses: actions/checkout@v4
  - uses: ./.github/actions/setup-project
    with:
      node-version: '20'
```

### Reusable Workflows

`.github/workflows/reusable-deploy.yml`:
```yaml
name: Reusable Deploy

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
    secrets:
      deploy-token:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4

      - run: ./deploy.sh
        env:
          DEPLOY_TOKEN: ${{ secrets.deploy-token }}
          ENVIRONMENT: ${{ inputs.environment }}
```

**Usage**:
```yaml
name: Deploy Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
    secrets:
      deploy-token: ${{ secrets.PRODUCTION_TOKEN }}
```

## Performance Optimization

### Dependency Caching

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

### Docker Layer Caching

```yaml
- uses: docker/build-push-action@v5
  with:
    context: .
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### Parallelization

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: npm run lint

  test-unit:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:unit

  test-integration:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:integration

  # All run in parallel
```

### Conditional Job Execution

```yaml
jobs:
  deploy:
    # Skip deploy on draft PRs
    if: github.event.pull_request.draft == false
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh
```

## Debugging Workflows

### Enable Debug Logging

Set repository secrets:
- `ACTIONS_RUNNER_DEBUG`: `true`
- `ACTIONS_STEP_DEBUG`: `true`

### Debug Step

```yaml
- name: Debug Info
  run: |
    echo "Event: ${{ github.event_name }}"
    echo "Ref: ${{ github.ref }}"
    echo "SHA: ${{ github.sha }}"
    echo "Actor: ${{ github.actor }}"
    env
```

### Interactive Debugging with tmate

```yaml
- name: Setup tmate session
  if: failure()
  uses: mxschmitt/action-tmate@v3
  timeout-minutes: 15
```

## Best Practices

### Security
- Use secrets for sensitive data
- Pin action versions to SHA: `uses: actions/checkout@8e5e7e5a...`
- Minimize token permissions
- Use environment protection rules
- Enable branch protection with required checks

### Performance
- Cache dependencies aggressively
- Use matrix strategies for parallel testing
- Minimize checkout depth when possible
- Use artifacts for job-to-job data transfer
- Optimize Docker builds with multi-stage builds

### Maintainability
- Use reusable workflows for common patterns
- Create composite actions for repeated steps
- Document workflow purpose and triggers
- Use meaningful job and step names
- Keep workflows focused (single responsibility)

### Reliability
- Set appropriate timeouts
- Use `continue-on-error` strategically
- Implement retry logic for flaky tests
- Monitor workflow run times
- Clean up old artifacts and caches

## Common Patterns

### PR Comment on Failure

```yaml
- name: Comment on PR
  if: failure() && github.event_name == 'pull_request'
  uses: actions/github-script@v7
  with:
    script: |
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: '❌ Tests failed. Please check the workflow logs.'
      })
```

### Auto-merge Dependabot PRs

```yaml
name: Auto-merge Dependabot

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  auto-merge:
    if: github.actor == 'dependabot[bot]'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - run: npm ci
      - run: npm test

      - uses: gh enable-auto-merge --merge
        if: success()
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Notify on Deploy

```yaml
- name: Slack Notification
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Deploy to ${{ inputs.environment }}: ${{ job.status }}'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## Troubleshooting

### Common Issues

**Workflow not triggering**:
- Check branch filters match actual branch names
- Verify workflow file is in `.github/workflows/`
- Ensure YAML syntax is valid

**Job skipped**:
- Check `if` conditions
- Verify `needs` dependencies succeeded
- Check branch protection rules

**Timeout**:
- Default timeout is 360 minutes
- Set explicit timeout: `timeout-minutes: 30`
- Optimize long-running steps

**Permission denied**:
- Update workflow permissions:
  ```yaml
  permissions:
    contents: write
    pull-requests: write
  ```

**Secrets not available**:
- Verify secret names match exactly (case-sensitive)
- Check secret scope (repo, organization, environment)
- Ensure workflow has access to environment secrets

---

## Local Workflow Patterns (Your Repos)

### Python + uv CI (mcp-vector-search)

- Install uv: `astral-sh/setup-uv@v3` and `uv python install 3.11`.
- Use `uv sync --dev` and run `uv run ruff`, `uv run mypy`, `uv run pytest`.
- Use OS + Python version matrix and upload coverage to Codecov on linux.

### Node + pnpm CI (ai-code-review)

- Use `pnpm/action-setup@v4` and `actions/setup-node@v4` with pnpm cache.
- Install with `pnpm install --frozen-lockfile`, then `pnpm run lint`, `pnpm run build:types`, `pnpm test`.

### Release on Tags

- Trigger on `push` tags `v*`.
- Build, create GitHub Release notes, and publish to npm or PyPI.
- Use `pypa/gh-action-pypi-publish@release/v1` or `NODE_AUTH_TOKEN` for npm publish.

### Homebrew Update Pipeline

- Trigger on `workflow_run` after CI success.
- Run `scripts/update_homebrew_formula.py` with `HOMEBREW_TAP_TOKEN`.
- On failure, open an issue with manual update steps.

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Actions Marketplace](https://github.com/marketplace?type=actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [GitHub Actions Toolkit](https://github.com/actions/toolkit)
- [Awesome Actions](https://github.com/sdras/awesome-actions)
