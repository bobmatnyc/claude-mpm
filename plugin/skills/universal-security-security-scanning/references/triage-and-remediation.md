# Triage and Remediation Playbook

## Triage Flow

1) **Confirm the finding**
- Reproduce locally or in a minimal test case.
- Identify whether the finding is code, dependency, configuration, or secret-related.

2) **Classify severity**
- Impact: data loss, account takeover, RCE, privilege escalation, availability.
- Likelihood: exposed surface area, exploitability, required access.

3) **Pick a remediation strategy**
- Patch code (preferred).
- Upgrade/replace dependency.
- Add runtime mitigations (WAF/rate limiting) as a stopgap, not a substitute.

4) **Verify**
- Add tests for the vulnerable behavior (negative tests and abuse cases).
- Re-run scans and ensure the finding is gone or properly suppressed.

## Dependency Vulnerabilities

Checklist:
- Upgrade the smallest scope first (patch/minor updates before major).
- Prefer direct dependency upgrades; use overrides/resolutions only as a bridge.
- Confirm the vulnerable code path is not reachable when considering risk acceptance.

## Secrets

Treat secrets as an incident:
- Rotate the secret and revoke the old one.
- Identify exposure window (commits, CI logs, artifacts).
- Add secret scanning to prevent recurrence.

## False Positives and Exceptions

Avoid permanent suppressions. Require:
- reason
- owner
- expiry date
- link to ticket or risk acceptance

Example exception record:

```yaml
exceptions:
  - id: "SEMGRP-1234"
    reason: "False positive: input is constant and validated upstream"
    owner: "security@team"
    expires: "2026-03-01"
    ticket: "SEC-456"
```

Review exceptions on a schedule and delete expired entries.

