---
name: trusty-services
description: Install and configure trusty-memory and trusty-search for persistent AI memory and semantic code search
type: migration
version: "2.0.0"
category: migration
state_key: trusty-services
protocol: migration-wizard
services:
  - trusty-memory
  - trusty-search
recommended: true

# ---- Phase 1: Detection ----
check_commands:
  - "which trusty-memory"
  - "which trusty-search"
health_checks:
  - url: "http://localhost:3038/health"
    service: trusty-memory
  - url: "http://localhost:7878/health"
    service: trusty-search

# ---- Phase 2: System requirements ----
system_requirements:
  min_ram_gb: 4
  min_disk_gb: 2
  tools_required:
    - name: cargo
      check: "cargo --version"
      install_hint: |
        Install Rust (which provides cargo) via rustup:
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
        Then restart your shell and re-run /mpm-migrate trusty-services.

# ---- Phase 3: Installation ----
install_commands:
  - "claude-mpm setup trusty-memory trusty-search"
install_script: "scripts/install-trusty.sh"

# ---- Phase 4: Verification ----
verify_commands:
  - "trusty-memory --version"
  - "trusty-search --version"
verify_scripts:
  - "scripts/verify-trusty.sh"

# ---- Phase 5: Completion ----
post_install_notes: |
  Trusty services are installed and running:
    - trusty-memory at http://localhost:3038 (persistent cross-session memory)
    - trusty-search at http://localhost:7878 (semantic code search)

  Both are wired into .mcp.json. Restart Claude Code to pick up the new MCP
  tools. Verify with `claude-mpm doctor`.

tags: [migration, setup, trusty, memory, search, wizard]
---

# Trusty Services

This is a **migration subskill**. It declares WHAT to install in its
frontmatter. The HOW lives in the parent protocol:
[`migration-wizard/SKILL.md`](../migration-wizard/SKILL.md).

> **Always load the migration-wizard protocol before executing this skill.**
> The five-phase wizard (user choice → detect → check → install → verify →
> complete) is defined there, not here.

## Why install these?

`trusty-memory` and `trusty-search` are optional Rust services that give
claude-mpm two capabilities the base install lacks:

- **trusty-memory**: persistent, hierarchical knowledge graph (palace / wing
  / room / closet / drawer) that survives across sessions. Lets agents
  remember context from previous conversations without re-explaining.
- **trusty-search**: hybrid semantic + BM25 + knowledge-graph code search
  with RRF fusion. Drop-in replacement for `mcp-vector-search` with better
  recall on large codebases.

Together they raise the ceiling on what cross-session workflows can
accomplish — but they require Rust, ~2GB disk, and a one-time setup pass,
which is why they ship as a migration skill rather than a default
dependency.

## What to expect during install

The protocol's Phase 3 delegates to `scripts/install-trusty.sh`, which:

1. Prefers `claude-mpm setup trusty-memory trusty-search` (the consolidated
   command that handles `cargo install`, launchd plist creation, and
   `.mcp.json` wiring atomically).
2. Falls back to per-binary `claude-mpm setup <name>` on older claude-mpm.
3. Falls back to raw `cargo install` if `claude-mpm` is unavailable; in
   that case daemon startup and MCP wiring become manual steps.

A typical install takes 3-8 minutes (mostly cargo compile time).

## Known gotchas

- **macOS, `linker 'cc' not found`** — install Xcode Command Line Tools
  with `xcode-select --install`, then retry.
- **`cargo install` SSL error** — usually a corporate proxy. Configure
  `CARGO_HTTP_PROXY` and retry.
- **`Address already in use`** — a previous daemon is still running. Run
  `pkill -f trusty-memory; pkill -f trusty-search` and retry.
- **Default ports** — memory uses :3038, search uses :7878. If those are
  occupied, the daemons will pick alternates and write the actual ports to
  `~/.trusty-*/address.json`; the health checks in this skill assume the
  defaults.

## Verification

Phase 4 runs `scripts/verify-trusty.sh`, which checks:

1. Both binaries on `$PATH`.
2. Both daemons responding to `/health`.
3. `.mcp.json` (if present in CWD) references trusty server entries.
4. On macOS, launchd plists exist under `~/Library/LaunchAgents/`.

Verification must pass completely before Phase 5 records completion. A
partial install (binary present, daemon down) will be re-detected on the
next session and the wizard will offer to repair it.
