# Agent Integration Guide for env-manager

This guide shows how Claude MPM agents should use the env-manager skill for environment variable validation, security scanning, and deployment preparation.

## Overview

The env-manager skill provides agents with systematic environment variable management capabilities. Agents can delegate environment validation tasks to this skill or invoke it directly for automated checks.

## Skill Invocation Pattern

### Basic Invocation

Agents can invoke the env-manager skill using the standard Claude MPM skill invocation pattern:

```
Use env-manager skill for environment variable validation
```

### Specific Task Invocation

For targeted tasks, agents can be more specific:

```
Use env-manager skill to validate Next.js environment variables for security issues
```

```
Use env-manager skill to generate .env.example documentation
```

```
Use env-manager skill to compare .env with .env.example before deployment
```

## Agent Usage Patterns

### Pattern 1: Pre-Deployment Validation

**Scenario:** Agent needs to validate environment before deployment

```python
# Agent workflow
1. Identify deployment target (Vercel, Railway, etc.)
2. Invoke env-manager skill: "Validate .env for Next.js deployment to Vercel"
3. Parse validation results
4. If errors: Report to user, block deployment
5. If warnings: Report to user, request confirmation
6. If success: Proceed with deployment
```

**Example skill invocation:**
```
I need to validate the Next.js environment configuration before deploying to Vercel.
Use env-manager skill to check .env.local for:
- Next.js specific issues (NEXT_PUBLIC_ prefix usage)
- Security issues (exposed secrets)
- Missing required variables
- Deployment readiness
```

### Pattern 2: Security Scanning

**Scenario:** Security agent needs to scan for exposed secrets

```python
# Security agent workflow
1. Locate .env files in project
2. Invoke env-manager: "Scan for security issues in environment variables"
3. Parse security warnings
4. Generate security report
5. Recommend fixes for found issues
```

**Example skill invocation:**
```
Use env-manager skill to perform security scan of .env.local:
- Check for secrets in client-exposed variables (NEXT_PUBLIC_, VITE_, REACT_APP_)
- Validate secret formats
- Identify potential credential leaks
- Report security warnings
```

### Pattern 3: Documentation Generation

**Scenario:** Agent needs to generate .env.example for repository

```python
# Documentation agent workflow
1. Read current .env file
2. Invoke env-manager: "Generate .env.example with sanitized values"
3. Review generated file
4. Add to git (ensure .env.example, not .env)
5. Update README with environment setup instructions
```

**Example skill invocation:**
```
Use env-manager skill to generate .env.example from .env:
- Sanitize all secret values
- Keep structure and variable names
- Add helpful comments for required variables
- Ensure safe for git commit
```

### Pattern 4: Onboarding Assistance

**Scenario:** Agent helps new developer set up environment

```python
# Onboarding agent workflow
1. Guide user to copy .env.example to .env
2. Invoke env-manager: "Compare .env with .env.example"
3. Report missing variables to user
4. Guide user to fill in missing values
5. Re-validate until complete
```

**Example skill invocation:**
```
Use env-manager skill to verify new developer's environment setup:
- Compare .env with .env.example
- Report missing required variables
- Identify extra undocumented variables
- Validate all values are filled in (no empty values)
```

### Pattern 5: CI/CD Integration

**Scenario:** CI/CD agent validates environment in pipeline

```python
# CI/CD agent workflow
1. Locate .env.example in repository
2. Invoke env-manager: "Validate .env.example with strict mode and JSON output"
3. Parse JSON results
4. If validation fails: Fail pipeline with details
5. If validation passes: Continue pipeline
```

**Example skill invocation:**
```
Use env-manager skill for CI/CD validation:
- Validate .env.example structure
- Use strict mode (warnings as errors)
- Output JSON for parsing
- Return exit code for pipeline
```

## Expected Outputs

### Success Response

When validation passes:

```json
{
  "status": "success",
  "message": "Validation successful",
  "stats": {
    "total_vars": 15,
    "errors": 0,
    "warnings": 0
  }
}
```

**Agent action:** Proceed with next step in workflow

### Error Response

When validation fails:

```json
{
  "status": "error",
  "errors": [
    {
      "line": 12,
      "key": "DATABASE_URL",
      "message": "Empty value not allowed",
      "severity": "error"
    }
  ],
  "stats": {
    "total_vars": 15,
    "errors": 1,
    "warnings": 0
  }
}
```

**Agent action:**
1. Report errors to user
2. Suggest fixes
3. Block deployment/pipeline
4. Request user to fix errors and retry

### Warning Response

When warnings are found:

```json
{
  "status": "warning",
  "warnings": [
    {
      "line": 5,
      "key": "NEXT_PUBLIC_API_KEY",
      "message": "Potential secret in client-exposed variable",
      "severity": "warning"
    }
  ],
  "stats": {
    "total_vars": 15,
    "errors": 0,
    "warnings": 1
  }
}
```

**Agent action:**
1. Report warnings to user
2. Explain security implications
3. Request confirmation to proceed
4. In strict mode: Treat as error

## Error Handling

### File Not Found

```python
if file_not_found:
    agent.report("Environment file not found")
    agent.suggest("Create .env file from .env.example: cp .env.example .env")
    agent.guide_user_to_fill_values()
```

### Validation Errors

```python
if validation_errors:
    agent.report_errors(errors)
    agent.suggest_fixes_for_each_error()
    agent.block_deployment()
    agent.request_retry_after_fixes()
```

### Security Warnings

```python
if security_warnings:
    agent.highlight_security_risks()
    agent.explain_client_exposure()
    agent.suggest_moving_to_server_side()
    agent.request_confirmation_or_fix()
```

### Missing Variables

```python
if missing_vars:
    agent.list_missing_vars()
    agent.guide_where_to_find_values()
    agent.explain_importance_of_each_var()
    agent.validate_after_user_adds_vars()
```

## JSON Output Parsing

Agents should use `--json` flag for structured output:

```bash
python3 scripts/validate_env.py .env --framework nextjs --json
```

**Parsing JSON output:**

```python
import json
import subprocess

result = subprocess.run(
    ["python3", "scripts/validate_env.py", ".env", "--framework", "nextjs", "--json"],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)

if data["valid"]:
    # Validation passed
    proceed_with_deployment()
elif data["errors"]:
    # Validation failed
    report_errors_to_user(data["errors"])
    block_deployment()
elif data["warnings"]:
    # Warnings found
    report_warnings_to_user(data["warnings"])
    request_confirmation()
```

## Agent-Specific Workflows

### nextjs-engineer Agent

**Use cases:**
- Pre-deployment validation for Vercel
- NEXT_PUBLIC_ variable security checks
- .env.local vs .env.production management

**Example workflow:**
```
1. User: "Deploy to Vercel"
2. Agent validates .env.local with --framework nextjs
3. Agent checks for NEXT_PUBLIC_ secrets
4. Agent compares with Vercel environment variables
5. Agent proceeds with deployment or reports issues
```

### security Agent

**Use cases:**
- Secret exposure scanning
- Client-side variable security audit
- Credential format validation

**Example workflow:**
```
1. User: "Run security audit"
2. Agent scans all .env* files
3. Agent checks for exposed secrets in NEXT_PUBLIC_ vars
4. Agent validates .gitignore covers .env files
5. Agent generates security report
```

### vercel-ops-agent Agent

**Use cases:**
- Platform environment sync
- Deployment configuration validation
- Environment parity checks

**Example workflow:**
```
1. User: "Sync environment to Vercel"
2. Agent compares local .env with Vercel project settings
3. Agent identifies missing/different variables
4. Agent generates vercel.json or CLI commands
5. Agent syncs to platform (with confirmation)
```

### devops Agent

**Use cases:**
- CI/CD pipeline validation
- Multi-environment management
- .env.example maintenance

**Example workflow:**
```
1. User: "Set up CI/CD for environment validation"
2. Agent creates GitHub Actions workflow
3. Agent configures env-manager validation step
4. Agent sets up strict mode for quality gate
5. Agent tests pipeline with .env.example
```

### onboarding-assistant Agent

**Use cases:**
- New developer environment setup
- Guided .env configuration
- Validation and troubleshooting

**Example workflow:**
```
1. User: "New developer needs environment setup"
2. Agent guides: cp .env.example .env
3. Agent runs validation to find missing vars
4. Agent explains each required variable
5. Agent validates complete setup
6. Agent confirms ready for development
```

## Best Practices for Agents

### 1. Always Validate Before Deployment

```python
def deploy_to_platform():
    # ✅ Good: Validate first
    validation_result = run_env_validation()
    if not validation_result.valid:
        report_errors_and_block()
        return

    proceed_with_deployment()
```

### 2. Use Framework-Specific Validation

```python
def validate_for_framework(framework):
    # ✅ Good: Framework-aware
    cmd = f"python3 scripts/validate_env.py .env --framework {framework}"

    # ❌ Bad: Generic validation only
    # cmd = "python3 scripts/validate_env.py .env"
```

### 3. Parse JSON for Structured Handling

```python
# ✅ Good: Structured output
result = run_validation(json=True)
data = json.loads(result.stdout)
handle_each_error(data["errors"])

# ❌ Bad: Parse text output
# result = run_validation()
# grep for errors in text
```

### 4. Explain Security Warnings

```python
def handle_security_warning(warning):
    # ✅ Good: Explain the risk
    agent.explain(f"{warning.key} is exposed to client-side code")
    agent.explain("This means users can see this value in their browser")
    agent.suggest("Move to server-side variable or use publishable key")

    # ❌ Bad: Just show the warning
    # print(warning)
```

### 5. Guide Users to Fix Issues

```python
def handle_missing_variable(var_name):
    # ✅ Good: Actionable guidance
    agent.explain(f"{var_name} is required but missing")
    agent.explain("This variable is used for: <purpose>")
    agent.suggest(f"Add to .env: {var_name}=<value>")
    agent.guide("You can find this value in: <location>")

    # ❌ Bad: Just report it's missing
    # print(f"Missing: {var_name}")
```

### 6. Use Strict Mode in CI/CD

```python
def ci_cd_validation():
    # ✅ Good: Strict mode in CI
    result = run_validation(strict=True)
    # Warnings will fail the pipeline

    # ❌ Bad: Ignore warnings in CI
    # result = run_validation()
```

### 7. Never Log Actual Secret Values

```python
def report_validation_result(result):
    # ✅ Good: Report structure, not values
    agent.report(f"Found {len(result.errors)} errors")
    agent.report_error_details_without_values()

    # ❌ Bad: Log actual values
    # print(f"DATABASE_URL={os.getenv('DATABASE_URL')}")  # NEVER!
```

## Integration Checklist

When integrating env-manager into an agent workflow:

- [ ] Identify validation trigger (deployment, commit, security scan)
- [ ] Determine appropriate framework (nextjs, vite, react, nodejs, flask)
- [ ] Choose validation mode (normal, strict, quiet)
- [ ] Set up JSON output parsing
- [ ] Handle all error types (file not found, validation errors, warnings)
- [ ] Provide actionable guidance for each error type
- [ ] Implement retry logic after user fixes issues
- [ ] Never log actual secret values
- [ ] Test with various .env file scenarios
- [ ] Document agent's env-manager usage in agent template

## Example Agent Implementation

Here's a complete example of a deployment agent using env-manager:

```python
class DeploymentAgent:
    def __init__(self):
        self.env_manager = EnvManagerSkill()

    def deploy_to_vercel(self, env_file=".env.local"):
        """Deploy Next.js app to Vercel with env validation."""

        # Step 1: Pre-deployment validation
        print("🔍 Validating environment variables...")
        result = self.env_manager.validate(
            file=env_file,
            framework="nextjs",
            strict=True,
            json=True
        )

        # Step 2: Parse results
        data = json.loads(result.stdout)

        # Step 3: Handle errors
        if data.get("errors"):
            self.report_errors(data["errors"])
            print("❌ Deployment blocked due to validation errors")
            return False

        # Step 4: Handle warnings
        if data.get("warnings"):
            self.report_warnings(data["warnings"])
            if not self.request_user_confirmation():
                print("⚠️  Deployment cancelled by user")
                return False

        # Step 5: Validate completeness
        if not self.compare_with_example(env_file):
            print("❌ Missing required variables")
            return False

        # Step 6: Proceed with deployment
        print("✅ Environment validation passed")
        print("🚀 Deploying to Vercel...")
        self.deploy()
        return True

    def report_errors(self, errors):
        """Report validation errors with actionable guidance."""
        print(f"\n❌ Found {len(errors)} validation error(s):\n")
        for error in errors:
            print(f"Line {error['line']}: {error['key']}")
            print(f"  Error: {error['message']}")
            print(f"  Fix: {self.get_fix_suggestion(error)}\n")

    def report_warnings(self, warnings):
        """Report validation warnings with security context."""
        print(f"\n⚠️  Found {len(warnings)} warning(s):\n")
        for warning in warnings:
            print(f"{warning['key']}: {warning['message']}")
            if "client-exposed" in warning['message']:
                print("  ⚠️  Security risk: This value will be visible in browser")
                print("  Fix: Move to server-side variable or use publishable key")
            print()

    def compare_with_example(self, env_file):
        """Ensure all required variables are present."""
        result = self.env_manager.validate(
            file=env_file,
            compare_with=".env.example",
            json=True
        )
        data = json.loads(result.stdout)

        if data.get("missing_vars"):
            print(f"❌ Missing required variables: {', '.join(data['missing_vars'])}")
            print("Add these to your .env file before deploying")
            return False

        return True

    def request_user_confirmation(self):
        """Request user confirmation for warnings."""
        response = input("⚠️  Warnings found. Proceed anyway? (y/N): ")
        return response.lower() == 'y'

    def get_fix_suggestion(self, error):
        """Provide fix suggestion based on error type."""
        if "empty value" in error["message"].lower():
            return f"Add a value for {error['key']}"
        elif "duplicate" in error["message"].lower():
            return f"Remove duplicate definition of {error['key']}"
        elif "invalid format" in error["message"].lower():
            return f"Fix format: {error['key']}=value"
        else:
            return "Review and fix the issue"
```

## Support and Resources

- **Skill Documentation**: [README.md](README.md)
- **Validation Reference**: [references/validation.md](references/validation.md)
- **Security Reference**: [references/security.md](references/security.md)
- **Framework Reference**: [references/frameworks.md](references/frameworks.md)
- **Troubleshooting**: [references/troubleshooting.md](references/troubleshooting.md)

## Contributing

When adding env-manager integration to agents:

1. Follow the patterns in this guide
2. Test with various .env file scenarios
3. Document the integration in agent template
4. Submit examples to this guide
5. Ensure security best practices (never log secrets!)

---

**Version**: 1.0.0
**Last Updated**: 2025-11-13
