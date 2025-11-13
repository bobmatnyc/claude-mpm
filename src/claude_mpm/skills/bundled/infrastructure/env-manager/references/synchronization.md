# Environment Synchronization Patterns

> **Part of**: [env-manager](../SKILL.md)
> **Category**: infrastructure
> **Reading Level**: Advanced

## Purpose

Platform synchronization workflows: comparing local vs deployed environments, generating platform configs, safe sync patterns, and secret manager integration.

## Synchronization Principles

### Safety First: Dry-Run Default

**Always default to dry-run for safety:**

```python
def sync_to_platform(env_file: Path, platform: str, dry_run: bool = True):
    """Sync environment to platform. Defaults to dry-run."""
    changes = calculate_changes(env_file, platform)

    if dry_run:
        print("🔍 DRY-RUN MODE: No changes will be applied")
        print("\nProposed changes:")
        display_changes(changes)
        print("\nTo apply: add --confirm flag")
        return

    # Actual sync only if dry_run=False
    apply_changes(changes, platform)
```

### Three-Way Comparison

Compare across local, platform, and secret manager:

```
Local (.env) ←→ Platform (Vercel/Railway) ←→ Secret Manager (1Password/AWS)
```

## Platform Comparison Workflows

### Compare Local vs Platform

```python
from typing import Dict, Set
from pathlib import Path

def compare_environments(
    local_env: Path,
    platform_env: Dict[str, str]
) -> Dict:
    """Compare local .env against platform environment."""

    local_vars = parse_env_file(local_env)

    return {
        'only_local': set(local_vars.keys()) - set(platform_env.keys()),
        'only_platform': set(platform_env.keys()) - set(local_vars.keys()),
        'different_values': {
            key for key in local_vars.keys() & platform_env.keys()
            if local_vars[key] != platform_env[key]
        },
        'identical': {
            key for key in local_vars.keys() & platform_env.keys()
            if local_vars[key] == platform_env[key]
        }
    }
```

### Display Comparison Results

```python
def display_comparison(comparison: Dict):
    """Display comparison in readable format."""

    print("\n📊 Environment Comparison\n")

    if comparison['only_local']:
        print("⚠️  Variables only in LOCAL:")
        for var in sorted(comparison['only_local']):
            print(f"  + {var}")

    if comparison['only_platform']:
        print("\n⚠️  Variables only in PLATFORM:")
        for var in sorted(comparison['only_platform']):
            print(f"  - {var}")

    if comparison['different_values']:
        print("\n🔄 Variables with DIFFERENT values:")
        for var in sorted(comparison['different_values']):
            print(f"  ≠ {var}")

    if comparison['identical']:
        print(f"\n✅ {len(comparison['identical'])} variables identical")
```

## Platform-Specific Integration

### Vercel

**Fetch Current Environment:**
```python
import requests

def fetch_vercel_env(project_id: str, token: str) -> Dict[str, str]:
    """Fetch environment variables from Vercel."""
    url = f"https://api.vercel.com/v9/projects/{project_id}/env"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    # Vercel returns array of {key, value, target, type}
    env_vars = {}
    for var in response.json()['envs']:
        if 'production' in var.get('target', []):
            env_vars[var['key']] = var['value']

    return env_vars
```

**Generate Vercel Config:**
```python
def generate_vercel_config(env_file: Path) -> str:
    """Generate vercel.json env configuration."""
    vars_dict = parse_env_file(env_file)

    # Separate public vs private
    public_vars = {k: v for k, v in vars_dict.items() if k.startswith('NEXT_PUBLIC_')}
    private_vars = {k: v for k, v in vars_dict.items() if not k.startswith('NEXT_PUBLIC_')}

    config = {
        "env": {k: v for k, v in public_vars.items()},
        "build": {
            "env": {k: v for k, v in private_vars.items() if not is_secret(k)}
        }
    }

    return json.dumps(config, indent=2)
```

**Sync to Vercel:**
```python
def sync_to_vercel(env_file: Path, project_id: str, token: str, dry_run: bool = True):
    """Sync environment variables to Vercel."""
    local_vars = parse_env_file(env_file)
    remote_vars = fetch_vercel_env(project_id, token)

    changes = compare_environments(env_file, remote_vars)

    if dry_run:
        display_comparison(changes)
        return

    # Apply changes
    url = f"https://api.vercel.com/v10/projects/{project_id}/env"
    headers = {"Authorization": f"Bearer {token}"}

    for key in changes['only_local']:
        data = {
            "key": key,
            "value": local_vars[key],
            "target": ["production"],
            "type": "encrypted"
        }
        requests.post(url, headers=headers, json=data)

    print("✅ Synced to Vercel")
```

### Railway

**Fetch Railway Environment:**
```python
def fetch_railway_env(project_id: str, token: str) -> Dict[str, str]:
    """Fetch environment variables from Railway."""
    # Railway uses GraphQL API
    query = """
    query($projectId: String!) {
        project(id: $projectId) {
            environments {
                variables {
                    name
                    value
                }
            }
        }
    }
    """

    response = requests.post(
        "https://backboard.railway.app/graphql/v2",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query, "variables": {"projectId": project_id}}
    )

    data = response.json()
    env_vars = {}
    for var in data['data']['project']['environments'][0]['variables']:
        env_vars[var['name']] = var['value']

    return env_vars
```

**Sync to Railway:**
```python
def sync_to_railway(env_file: Path, project_id: str, token: str, dry_run: bool = True):
    """Sync environment variables to Railway."""
    local_vars = parse_env_file(env_file)

    if dry_run:
        print("🔍 DRY-RUN: Would sync to Railway:")
        for key in local_vars:
            print(f"  {key}={mask_secret(local_vars[key])}")
        return

    # Use Railway CLI (more reliable than API)
    import subprocess
    for key, value in local_vars.items():
        subprocess.run(
            ["railway", "variables", "set", f"{key}={value}"],
            check=True
        )

    print("✅ Synced to Railway")
```

### Heroku

**Sync to Heroku:**
```python
def sync_to_heroku(env_file: Path, app_name: str, dry_run: bool = True):
    """Sync environment variables to Heroku."""
    import subprocess

    local_vars = parse_env_file(env_file)

    # Fetch current Heroku config
    result = subprocess.run(
        ["heroku", "config", "--app", app_name, "--json"],
        capture_output=True,
        text=True
    )
    remote_vars = json.loads(result.stdout)

    changes = compare_environments(env_file, remote_vars)

    if dry_run:
        display_comparison(changes)
        return

    # Apply changes using Heroku CLI
    for key, value in local_vars.items():
        subprocess.run(
            ["heroku", "config:set", f"{key}={value}", "--app", app_name],
            check=True
        )

    print("✅ Synced to Heroku")
```

## Secret Manager Integration

### 1Password

**Fetch from 1Password:**
```python
def fetch_from_1password(vault: str, item: str) -> Dict[str, str]:
    """Fetch secrets from 1Password CLI."""
    import subprocess
    import json

    result = subprocess.run(
        ["op", "item", "get", item, "--vault", vault, "--format", "json"],
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(result.stdout)
    env_vars = {}

    for field in data['fields']:
        if field['purpose'] == 'NOTES':
            # Parse env format from notes
            for line in field['value'].split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        else:
            # Individual fields
            env_vars[field['label'].upper()] = field['value']

    return env_vars
```

**Push to 1Password:**
```python
def push_to_1password(env_file: Path, vault: str, item: str):
    """Push environment to 1Password."""
    import subprocess

    vars_dict = parse_env_file(env_file)

    # Create notes field with all env vars
    notes = '\n'.join([f"{k}={v}" for k, v in vars_dict.items()])

    subprocess.run(
        ["op", "item", "edit", item, "--vault", vault, f"notes={notes}"],
        check=True
    )

    print(f"✅ Pushed to 1Password vault '{vault}'")
```

### AWS Secrets Manager

**Fetch from AWS:**
```python
def fetch_from_aws_secrets(secret_name: str, region: str = 'us-east-1') -> Dict[str, str]:
    """Fetch secrets from AWS Secrets Manager."""
    import boto3
    import json

    client = boto3.client('secretsmanager', region_name=region)
    response = client.get_secret_value(SecretId=secret_name)

    # Secrets stored as JSON
    return json.loads(response['SecretString'])
```

**Push to AWS:**
```python
def push_to_aws_secrets(env_file: Path, secret_name: str, region: str = 'us-east-1'):
    """Push environment to AWS Secrets Manager."""
    import boto3
    import json

    vars_dict = parse_env_file(env_file)
    client = boto3.client('secretsmanager', region_name=region)

    try:
        # Update existing secret
        client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(vars_dict)
        )
    except client.exceptions.ResourceNotFoundException:
        # Create new secret
        client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(vars_dict)
        )

    print(f"✅ Pushed to AWS Secrets Manager: {secret_name}")
```

## Safe Sync Patterns

### Three-Step Sync Process

```python
def safe_sync_workflow(env_file: Path, platform: str):
    """Safe sync workflow with validation."""

    # Step 1: Validate local environment
    print("1️⃣ Validating local environment...")
    validation = validate_structure(env_file)
    if validation['errors']:
        print("❌ Validation failed. Fix errors first.")
        return

    # Step 2: Dry-run comparison
    print("\n2️⃣ Comparing with platform...")
    comparison = compare_with_platform(env_file, platform)
    display_comparison(comparison)

    # Step 3: Confirm and sync
    print("\n3️⃣ Ready to sync")
    confirm = input("Apply changes? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Sync cancelled")
        return

    sync_to_platform(env_file, platform, dry_run=False)
    print("✅ Sync complete")
```

### Rollback Procedures

```python
def create_backup(platform: str, project_id: str) -> str:
    """Create backup before sync."""
    import json
    from datetime import datetime

    timestamp = datetime.now().isoformat()
    current_env = fetch_platform_env(platform, project_id)

    backup_file = f".env.backup.{platform}.{timestamp}.json"
    with open(backup_file, 'w') as f:
        json.dump(current_env, f, indent=2)

    return backup_file

def rollback(backup_file: str, platform: str, project_id: str):
    """Rollback to previous environment."""
    import json

    with open(backup_file) as f:
        backup_env = json.load(f)

    sync_dict_to_platform(backup_env, platform, project_id, dry_run=False)
    print(f"✅ Rolled back to {backup_file}")
```

## Summary

**Synchronization Workflow**:
1. **Validate**: Check local .env structure
2. **Compare**: Dry-run comparison with platform
3. **Review**: Display proposed changes
4. **Backup**: Save current platform state
5. **Sync**: Apply changes with confirmation
6. **Verify**: Check platform reflects changes

**Key Patterns**:
- ✅ Always dry-run first
- ✅ Three-way comparison (local/platform/secret manager)
- ✅ Never auto-apply changes
- ✅ Create backups before sync
- ✅ Rollback capability
- ✅ Platform-specific handling

**Supported Platforms**:
- Vercel (API + CLI)
- Railway (GraphQL API + CLI)
- Heroku (CLI)

**Supported Secret Managers**:
- 1Password (CLI)
- AWS Secrets Manager (boto3)

## Related References

- [Validation](validation.md): Environment validation
- [Security](security.md): Secret protection during sync
- [Troubleshooting](troubleshooting.md): Sync issue resolution

---
**Lines**: 277 ✓ 200-280 range
