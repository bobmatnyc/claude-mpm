# Security Scanning Tooling Matrix

Use scanners as layers. Start with a small baseline that runs fast on every PR, then add deeper checks on a schedule.

## Baseline (High-Value, Low-Drama)

1) **Secrets scanning**
- Block merges on secrets and rotate immediately.

2) **Dependency vulnerability scanning**
- Gate on critical/high first; track the rest with SLAs.

3) **SAST (static analysis)**
- Start with high-confidence rules; expand as false positives are tamed.

4) **IaC and container scanning**
- Add when shipping images or managing infra-as-code.

## Matrix

| Layer | What It Catches | OSS-First Options | Notes |
| --- | --- | --- | --- |
| Secrets | API keys, tokens, credentials committed to git | `gitleaks`, `trufflehog`, `detect-secrets` | Prefer scanning diffs on PR and full history on schedule |
| Dependencies | CVEs in direct/transitive dependencies | `osv-scanner`, language audits | Reachability-aware tooling reduces noise when available |
| SAST | Bug patterns (injection, authz gaps, risky APIs) | `semgrep`, `codeql` | Prefer SARIF output for PR annotations |
| Container | OS/package CVEs in images | `trivy`, `grype` | Scan SBOMs or images; keep base images current |
| IaC | Misconfigurations in Terraform/K8s/Docker | `trivy config`, `checkov`, `tfsec` | Focus on critical misconfigs (public buckets, open security groups) |
| License/Policy | Forbidden licenses, risky dependencies | `cargo-deny`, `licensee` | Enforce at the boundary (new deps) to avoid churn |

## Language/Ecosystem Notes

### JavaScript/TypeScript

- Dependency scanning: OSV database tools, plus `npm audit`/`pnpm audit` as a quick local check.
- SAST: Semgrep rulesets and TypeScript-aware linters.
- Supply-chain: lockfile integrity, strict registries, scoped tokens.

### Python

- Dependency scanning: `pip-audit` (OSV) and lockfile discipline where possible.
- SAST: Semgrep and targeted linters (`bandit`) for common risky APIs.

### Go

- Dependency scanning: `govulncheck` for the Go ecosystem plus OSV scanning.
- SAST: Semgrep and focused Go security linters (`gosec`) when useful.

### Rust

- Dependency scanning: `cargo audit` (advisory DB) and `cargo deny` for policy.
- SAST: fewer generic tools; rely on targeted patterns and review of unsafe blocks.

## Output Formats (Make CI Reviewable)

- Prefer tools that can emit **SARIF** to integrate with code-scanning UIs.
- Publish machine-readable artifacts (JSON/SARIF) and a short Markdown summary to PRs.

