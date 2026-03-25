# Supply Chain and SBOM Basics

## Baseline Controls

- Use lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `poetry.lock`, `Cargo.lock`, `go.sum`).
- Pin CI actions and critical dependencies to known-good versions.
- Prefer least-privilege tokens for CI and restrict secret access.

## SBOM

Generate an SBOM to track components and support incident response:
- Produce SBOMs for release artifacts and container images.
- Store SBOMs alongside build artifacts.
- Use SBOMs to accelerate “are we affected?” queries during CVEs.

## Provenance and Signing

Add integrity signals for production artifacts:
- Sign container images and release artifacts.
- Record build provenance (who/what built it, from which commit).

## Dependency Policy

Enforce at ingestion time:
- block new critical vulnerabilities
- restrict high-risk licenses if required
- require ownership for dependency additions

Use “ratcheting” gates to reduce churn: only prevent regressions at first, then tighten.

