# Integration Catalog

This directory contains the catalog of available integrations for Claude MPM.

## Structure

Each integration is defined in its own subdirectory with an `integration.yaml` manifest:

```
catalog/
  _index.yaml           # Auto-generated catalog index (DO NOT EDIT)
  TEMPLATE.yaml         # Template for new integrations
  README.md             # This file
  ci/                   # CI validation scripts
    validate.py         # Catalog validation for CI/CD
  jsonplaceholder/      # Example integration
    integration.yaml    # Integration manifest
  github/               # GitHub API integration
    integration.yaml
  slack/                # Slack API integration
    integration.yaml
```

## Creating New Integrations

### Option 1: Interactive Wizard (Recommended)

Use the creation wizard to generate a new integration:

```bash
# Create in catalog directory (for contributors)
mpm integrate create --catalog

# Create in current directory
mpm integrate create

# Create in specific directory
mpm integrate create --output /path/to/dir
```

### Option 2: Manual Creation

1. Copy TEMPLATE.yaml to a new directory: `myservice/integration.yaml`
2. Fill in required fields: name, description, base_url, operations
3. Define credentials needed (API keys, OAuth, etc.)
4. Add health check endpoint
5. Test with: `mpm integrate validate myservice`

## Manifest Schema

See `TEMPLATE.yaml` for full schema. Key sections:

- **info**: Name, version, description
- **auth**: Authentication configuration (api_key, bearer, basic, none)
- **credentials**: Required credential definitions
- **operations**: Available API operations
- **health_check**: Endpoint for status checks

## Installation

Install an integration to your project:

```bash
mpm integrate add jsonplaceholder
```

This will:
1. Copy the manifest to `.claude/integrations/`
2. Prompt for required credentials
3. Generate agent skill file if needed

## Contributing to the Catalog

We welcome contributions! Follow these steps to add a new integration:

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/claude-mpm.git
cd claude-mpm
```

### 2. Create Your Integration

```bash
# Use the wizard for guided creation
mpm integrate create --catalog

# Or manually create from template
cp src/claude_mpm/integrations/catalog/TEMPLATE.yaml \
   src/claude_mpm/integrations/catalog/myapi/integration.yaml
```

### 3. Validate Your Integration

```bash
# Validate single integration
mpm integrate validate src/claude_mpm/integrations/catalog/myapi

# Validate entire catalog
mpm integrate validate-catalog
```

### 4. Rebuild the Index

After adding your integration, regenerate the catalog index:

```bash
mpm integrate rebuild-index
```

### 5. Test Locally

```bash
# Install your integration
mpm integrate add myapi

# Test operations
mpm integrate call myapi list_items
```

### 6. Submit a Pull Request

1. Commit your changes:
   ```bash
   git add src/claude_mpm/integrations/catalog/myapi/
   git commit -m "feat: add myapi integration"
   ```

2. Push and create a PR:
   ```bash
   git push origin my-integration-branch
   ```

3. Ensure CI checks pass

### Contribution Checklist

Before submitting your PR, verify:

- [ ] `integration.yaml` passes validation
- [ ] All required fields are present (name, version, description, base_url)
- [ ] At least one operation is defined
- [ ] Health check endpoint is configured
- [ ] Credentials have clear descriptions
- [ ] `_index.yaml` is regenerated
- [ ] CI validation passes

## CI Integration

The catalog includes CI validation scripts that run automatically:

```bash
# Run all validations (for CI)
python -m claude_mpm.integrations.catalog.ci.validate

# Or use the CLI
mpm integrate validate-catalog
```

### Exit Codes

- `0`: All validations passed
- `1`: One or more validations failed

### GitHub Actions Example

```yaml
name: Validate Catalog

on:
  push:
    paths:
      - 'src/claude_mpm/integrations/catalog/**'
  pull_request:
    paths:
      - 'src/claude_mpm/integrations/catalog/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e .
      - run: mpm integrate validate-catalog
      - run: mpm integrate rebuild-index --verify
```

## Batch Operations

For bulk operations, create a Python batch script:

```python
# my_batch.py
from claude_mpm.integrations.core.batch import BatchContext

async def run(ctx: BatchContext) -> None:
    """Batch operation example."""
    for item_id in range(1, 11):
        result = await ctx.client.call_operation("get_item", {"id": item_id})
        ctx.log_result("get_item", result)
```

Run with:

```bash
mpm integrate batch jsonplaceholder my_batch.py
```

## Questions?

- Open an issue for bugs or feature requests
- Check existing integrations for examples
- Read the [Integration Development Guide](../../../docs/integrations.md)
