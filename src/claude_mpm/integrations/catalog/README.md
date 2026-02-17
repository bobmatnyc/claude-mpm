# Integration Catalog

This directory contains the catalog of available integrations for Claude MPM.

## Structure

Each integration is defined in its own subdirectory with an `integration.yaml` manifest:

```
catalog/
  _index.yaml           # Catalog index with metadata
  TEMPLATE.yaml         # Template for new integrations
  README.md             # This file
  jsonplaceholder/      # Example integration
    integration.yaml    # Integration manifest
  github/               # GitHub API integration
    integration.yaml
  slack/                # Slack API integration
    integration.yaml
```

## Creating New Integrations

1. Copy TEMPLATE.yaml to a new directory: `myservice/integration.yaml`
2. Fill in required fields: name, description, base_url, operations
3. Define credentials needed (API keys, OAuth, etc.)
4. Add health check endpoint
5. Test with: `mpm integrate validate myservice`

## Manifest Schema

See `TEMPLATE.yaml` for full schema. Key sections:

- **info**: Name, version, description
- **auth**: Authentication configuration
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
