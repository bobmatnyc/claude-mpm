# Agent Capabilities Reference

**Version**: 4.20.1
**Last Updated**: 2025-11-06

Complete reference documentation for all Claude MPM specialized agents, their capabilities, routing configurations, and when to use them.

## Table of Contents

- [Operations Agents](#operations-agents)
  - [Secrets Operations Agent](#secrets-operations-agent)
  - [General Ops Agent](#general-ops-agent)
  - [Local Ops Agent](#local-ops-agent)
  - [GCP Ops Agent](#gcp-ops-agent)
  - [Vercel Ops Agent](#vercel-ops-agent)
  - [Clerk Ops Agent](#clerk-ops-agent)
- [Engineering Agents](#engineering-agents)
- [QA Agents](#qa-agents)
- [Documentation Agents](#documentation-agents)
- [Routing Priority Reference](#routing-priority-reference)

---

## Operations Agents

### Secrets Operations Agent

**Agent ID**: `secrets-ops-agent`
**Model**: Sonnet
**Authority**: ops
**Priority**: 90
**Version**: 1.0.0

#### Description

Use this agent when you need specialized assistance with secrets and credentials management using 1Password CLI and other secret backends. This agent provides targeted expertise for managing API keys, tokens, passwords, environment variables, and vault operations with strong security practices.

#### Core Capabilities

- **1Password CLI Integration** (primary backend)
  - Authentication and session management
  - Item retrieval and creation
  - Vault operations (list, create, share)
  - Secret injection with `op run`
  - Template-based `.env` generation with `op inject`

- **Environment Variable Management**
  - Generate `.env` files from secret backends
  - Validate required environment variables
  - Format validation (API keys, JWTs, UUIDs)
  - Secure credential injection

- **Multi-Backend Support**
  - 1Password CLI (primary)
  - Bitwarden CLI (alternative)
  - AWS Secrets Manager (cloud)
  - HashiCorp Vault (enterprise)

- **Secret Rotation Workflows**
  - Database credential rotation
  - API key rotation and validation
  - Automated secret lifecycle management

- **Security Best Practices**
  - Output sanitization (never log secrets)
  - Temporary credential cleanup
  - Session handling and expiration
  - Audit logging for secret access

#### When to Use

- Managing secrets and credentials for local development
- Fetching secrets from 1Password vaults
- Generating `.env` files from secret backends
- Rotating API keys and database credentials
- Setting up secure secret injection for services
- Configuring team secret sharing
- Integrating secrets into CI/CD pipelines
- Auditing secret access and usage

#### Routing Configuration

**Keywords**:
- secrets, credentials, 1password, op, vault
- api-keys, api-key, apikey, tokens, token
- passwords, password, environment-variables
- .env, .env.local, config/credentials
- secret-rotation, credential-injection

**File Paths**:
- `.env`, `.env.local`, `.env.template`
- `config/credentials`
- `secrets/`

**Message Patterns**:
- `fetch.*secret`
- `get.*credential`
- `1password`
- `generate.*env`
- `rotate.*password`
- `manage.*api.*key`

**Priority**: 90 (high priority for security-sensitive operations)

#### Memory Routing

The agent stores and retrieves context about:
- Secret retrieval patterns and conventions
- Vault organization and structure
- Common credential configurations
- Team secrets management workflows
- Security audit findings
- API key rotation schedules
- Environment-specific secret mappings
- Integration patterns with deployment tools

#### Example Usage

**Scenario**: Setting up local development environment with secrets

```
User: "I need to fetch database credentials from 1Password and create a .env file"

PM: "I'll use the secrets-ops-agent to securely fetch credentials from 1Password
     and generate your .env file with proper permissions."

[Delegates to secrets-ops-agent]

Secrets-Ops-Agent:
  1. Checks 1Password CLI authentication (op whoami)
  2. Creates .env.template with 1Password references
  3. Uses op inject to generate .env securely
  4. Sets proper file permissions (chmod 600)
  5. Adds .env to .gitignore
  6. Returns sanitized output (no secret values displayed)
```

**Why this agent?**:
- Specializes in 1Password CLI operations
- Understands secure credential handling
- Knows environment variable generation patterns
- Follows security best practices (no logging secrets)
- Has targeted expertise in secrets management workflows

#### Dependencies

**Required**:
- `1password-cli` (op)
- `jq`
- `openssl`
- `bash`

**Optional**:
- `bitwarden-cli` (bw)
- `aws-cli`
- `vault` (HashiCorp)

#### Related Agents

- **ops-agent**: General operations, delegates secrets tasks to secrets-ops-agent
- **security-agent**: Security auditing and vulnerability scanning
- **local-ops-agent**: Local infrastructure and process management

---

### General Ops Agent

**Agent ID**: `ops-agent`
**Model**: Sonnet
**Authority**: ops
**Priority**: 75

General-purpose operations agent for infrastructure, deployment, and system operations. Delegates specialized tasks to domain-specific ops agents.

**Core Capabilities**:
- Infrastructure provisioning
- Deployment orchestration
- System monitoring and health checks
- Log analysis
- Container orchestration
- CI/CD pipeline management

**When to Use**: General infrastructure and deployment tasks

**Delegates to**: secrets-ops-agent, local-ops-agent, gcp-ops-agent, vercel-ops-agent

---

### Local Ops Agent

**Agent ID**: `local-ops-agent`
**Model**: Sonnet
**Authority**: ops
**Priority**: 80

Specialized in local development infrastructure and process management.

**Core Capabilities**:
- Process management (start, stop, restart services)
- Health checks (HTTP, process, resource)
- Auto-restart with exponential backoff
- Memory leak detection
- Configuration via YAML
- Port management

**When to Use**: Local service deployment, process management, health monitoring

---

### GCP Ops Agent

**Agent ID**: `gcp-ops-agent`
**Model**: Sonnet
**Authority**: ops
**Priority**: 85

Google Cloud Platform operations specialist.

**Core Capabilities**:
- GCP service deployment
- Cloud Run management
- GKE orchestration
- Cloud SQL operations
- IAM configuration
- Monitoring and logging

**When to Use**: GCP-specific operations and deployments

---

### Vercel Ops Agent

**Agent ID**: `vercel-ops-agent`
**Model**: Sonnet
**Authority**: ops
**Priority**: 85

Vercel platform deployment specialist.

**Core Capabilities**:
- Vercel deployments
- Environment variable management
- Domain configuration
- Preview deployments
- Build optimization

**When to Use**: Vercel platform operations

---

### Clerk Ops Agent

**Agent ID**: `clerk-ops-agent`
**Model**: Sonnet
**Authority**: ops
**Priority**: 85

Clerk authentication service specialist.

**Core Capabilities**:
- Clerk integration setup
- Authentication flow configuration
- User management
- Webhook configuration
- SSO setup

**When to Use**: Clerk authentication integration and management

---

## Engineering Agents

Engineering agents are documented in the main agent patterns and templates. Key agents include:

- **engineer**: General-purpose engineer
- **python-engineer**: Python specialist (v2.3.0)
- **typescript-engineer**: TypeScript specialist
- **rust-engineer**: Rust specialist (v1.1.0)
- **golang-engineer**: Go specialist
- **react-engineer**: React specialist
- **nextjs-engineer**: Next.js specialist
- **data-engineer**: Data engineering specialist

See [agent-patterns.md](agent-patterns.md) for detailed documentation.

---

## QA Agents

- **qa-agent**: General QA and testing
- **api-qa-agent**: API testing specialist
- **web-qa-agent**: Web testing specialist

---

## Documentation Agents

- **documentation-agent**: Technical documentation specialist
- **content-agent**: Content creation and copywriting

---

## Routing Priority Reference

Agents are selected based on priority scores:

| Priority | Meaning | Use Cases |
|----------|---------|-----------|
| 90-100 | Critical/High | Security-sensitive, language-specific |
| 75-89 | Medium-high | Platform-specific, specialized domains |
| 50-74 | Medium | General-purpose agents |
| 25-49 | Low | Fallback agents |

### Priority Examples

- **90**: secrets-ops-agent (security-critical)
- **85**: GCP, Vercel, Clerk ops (platform-specific)
- **80**: local-ops-agent (local infrastructure)
- **75**: ops-agent (general ops)
- **100**: Language-specific engineers with exact matches

### Routing Algorithm

1. **Keyword Matching**: Match message keywords against agent routing keywords
2. **File Path Matching**: Match file paths in context against agent paths
3. **Pattern Matching**: Match message against regex patterns
4. **Priority Scoring**: Calculate priority score based on matches
5. **Selection**: Choose highest priority agent with sufficient matches

---

## Using This Reference

### For Users

When working with Claude MPM, understanding agent capabilities helps you:
- Frame requests to route to the right agent
- Understand why specific agents are chosen
- Know what to expect from each agent

### For Agent Creators

Use this reference to:
- Understand existing agent landscape
- Avoid capability overlap
- Design complementary agents
- Set appropriate priority levels

### For PM Agent

This reference informs routing decisions:
- Match capabilities to task requirements
- Delegate to most specialized agent
- Understand agent handoff patterns
- Coordinate multi-agent workflows

---

**Version History**:
- **1.0.0** (2025-11-06): Initial reference with secrets-ops-agent
- Added comprehensive secrets-ops-agent documentation
- Established reference format for future agents

**Maintained By**: Claude MPM Team