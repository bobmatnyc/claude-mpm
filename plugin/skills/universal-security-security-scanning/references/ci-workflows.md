# CI Workflows for Security Scanning

Treat scanning like tests: fast PR checks + deeper scheduled runs.

## Recommended Cadence

- **On every PR**: secrets + dependency scan + lightweight SAST (high-signal rules).
- **Nightly/weekly**: deeper SAST rulesets, full-history secret scan, container/IaC scans, SBOM generation.

## Gating Strategy

- **Secrets**: fail the build and rotate immediately.
- **Dependencies**: fail on critical/high initially; ratchet over time.
- **SAST/IaC/Container**: start as advisory, then gate on high-confidence rules.

## GitHub Actions Skeleton (Conceptual)

```yaml
name: security-scan

on:
  pull_request:
  schedule:
    - cron: "0 3 * * *"

jobs:
  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Secret scan
        run: |
          # Example: gitleaks/trufflehog/detect-secrets
          echo "run secret scanner here"

  deps:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Dependency vuln scan
        run: |
          # Example: osv-scanner + ecosystem-specific audits
          echo "run dependency scanner here"

  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: SAST scan
        run: |
          # Example: semgrep/codeql
          echo "run SAST here"
```

Replace the `run:` blocks with the chosen tools and configure:
- PR annotations (SARIF where possible)
- artifact uploads (raw reports)
- thresholds/filters for gating

## Practical Tips

- Cache dependencies to keep PR scans fast.
- Separate “advisory” jobs using `continue-on-error` until false positives are under control.
- Publish a short summary to the PR (counts by severity + top findings + links to artifacts).

