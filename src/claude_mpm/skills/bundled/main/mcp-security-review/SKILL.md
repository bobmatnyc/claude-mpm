---
name: mcp-security-review
description: Security review gate for MCP server installations. Checks provenance, classifies risk, enforces version pinning, and documents credentials exposure before any MCP is added to your environment.
version: 1.0.0
when_to_use: when installing, adding, configuring, or updating any MCP server
progressive_disclosure:
  level: 1
  references: []
  note: Intentionally compact. The protocol is the value, not reference depth.
---

# MCP Security Review

Gate that runs before any MCP server is installed or updated. MCP servers handle credentials (OAuth tokens, API keys, AWS profiles) and have network access. A compromised or malicious package can exfiltrate secrets silently.

## When to Activate

Any time a new MCP server is being installed, added, configured, or updated. Trigger phrases: "install MCP", "add MCP", "set up MCP", "configure MCP", "claude mcp add", "new tool connection".

## Step 1: Identify Provenance

Determine who published the package before installing anything.

| Signal | Official | Community |
|--------|----------|-----------|
| npm scope | `@salesforce/`, `@modelcontextprotocol/`, `@anthropic/` | `@username/`, unscoped |
| PyPI publisher | Vendor org | Individual maintainer |
| GitHub org | `github.com/aws/`, `github.com/figma/` | Personal account |
| Hosted URL | Vendor domain (`mcp.atlassian.com`, `app.pendo.io`) | Third-party domain |

## Step 2: Classify Risk

| Classification | Criteria | Required Action |
|----------------|----------|-----------------|
| **Vendor-hosted** | Runs on vendor's own domain | Install. Low risk. |
| **Vendor-published** | Published by vendor org on npm/PyPI | Install. Pin version. |
| **MCP org** | Published under `@modelcontextprotocol/` | Install. Pin version. |
| **Internal** | Built by your team, code reviewed | Install. |
| **Community (established)** | 500+ GitHub stars, active maintenance, permissive license | Pin version. Audit source. Document in CLAUDE.md. |
| **Community (unknown)** | Low stars, single maintainer, no audit trail | Do not install. Find an official alternative or build internally. |

## Step 3: Audit Community Packages

For any package classified as "Community (established)":

**Pin the version.** Never install unpinned.
- npm: `package@1.2.3` (not `package` or `package@latest`)
- PyPI/uvx: `package==1.2.3` (not `package`)
- In `~/.claude.json` or project MCP config, use the pinned specifier

**Read the source.** Clone the repo at the pinned tag and check for:
- Outbound network calls to unexpected domains (data exfiltration)
- Credential logging, caching, or forwarding beyond what the API requires
- Obfuscated code, eval/exec calls, or suspicious post-install scripts
- Dependency chains pulling in unexpected packages

**Map credential exposure.** Document exactly what secrets the package touches:
- OAuth tokens (which provider, what scopes)
- AWS credentials (access keys, assumed roles, profiles)
- API keys (which service, what permissions)
- Filesystem access (what paths it reads/writes)

## Step 4: Document

Add an entry to your project's CLAUDE.md or security config:

```markdown
| MCP | Package | Provenance | Status |
|-----|---------|------------|--------|
| Slack | @anthropic/slack-mcp | Official (MCP org) | Approved |
| Athena | @user/athena-mcp@1.0.1 | Community (pinned) | Flagged: handles AWS creds |
```

## Step 5: Ongoing Maintenance

- **Before updating** a community MCP version: read the changelog and diff between your pinned version and the new one. Look for new dependencies, changed network calls, or modified credential handling.
- **When an official alternative ships**: migrate to it and remove the community package.
- **Periodic re-check**: vendors release official MCPs without announcement. Search npm/PyPI for official packages quarterly.
- **If a package is compromised**: revoke any credentials it had access to immediately, then remove the package.

## Why This Matters

MCP servers run as child processes with access to your shell environment, filesystem, and any credentials passed to them. Unlike browser extensions (sandboxed) or npm packages (typically build-time only), MCP servers actively send and receive data on your behalf at runtime. A single malicious update to an unpinned community package can capture every OAuth token and API key in your environment.
