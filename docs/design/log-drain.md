# Configurable Cloud Log-Drain Design

## Overview & Goals

The log-drain feature provides a **configurable, privacy-respecting mechanism** to stream session telemetry and optional usage analytics to a cloud storage backend (AWS S3), enabling:

1. **Team analytics**: Aggregate token usage, model selection, cost, and agent utilization across developers.
2. **Debug & observability**: Retain session artifacts (resume logs, session reports) centrally for troubleshooting and team learning.
3. **Opt-out for Duetto**: Duetto-internal deployments ship with log-drain enabled by default via a separate `claude-mpm-duetto` preset package; individual developers can disable locally.
4. **Privacy-first for OSS**: Public/OSS deployments default to disabled; users explicitly opt in and choose payload level.
5. **Configurable payload granularity**: Four levels (0–3) control sensitivity: from telemetry-only (level 1) through full session content (level 3, gated behind consent).

---

## Payload Model: Levels 0–3

Log-drain operates in four granularity levels, defined by what data is captured and spooled. Each level is additive (level 3 includes level 2, which includes level 1):

| Level | Name | Content | Sensitivity | Consent Required | Use Case |
|-------|------|---------|-------------|------------------|----------|
| **0** | None | Nothing (drain disabled) | — | No | Opt-out completely. |
| **1** | Telemetry | Token counts, cost, model names, agent names, error codes, session duration, tool execution times. NO prompt or code content. | Low | No | Anonymous usage analytics, team metrics. |
| **2** | Session Summary | Level 1 + resume-log metadata (git branch, working dir, session accomplishments, agents used, tools invoked). NO raw prompt/code. | Medium | No | Debugging + session context reconstruction. |
| **3** | Full | Level 2 + raw session content: session-analyzer reports, tool excerpts, structured error details. MAY include prompt/code context. | High | **Yes** | Advanced troubleshooting, team learning, code patterns. |

### Data Sources by Level

#### Level 1: Telemetry
- **Source**: `commit-costs.jsonl`, `.claude-mpm/state/context-usage.json`
- **Captured**:
  - Token usage (input, output, cache)
  - Estimated cost (model-based pricing)
  - Model name, project ID, session duration
  - Tool execution count and error codes
  - Agent names invoked
  - Timestamp (ISO 8601)
- **Redaction**: None required (no content).
- **Size**: ~500 bytes per session.

#### Level 2: Session Summary
- **Source**: Level 1 + resume logs (`.claude-mpm/state/resume-logs/<session_id>.json`), manifest state
- **Captured**:
  - All of Level 1
  - Git branch at session start
  - Working directory (path, not content)
  - Session status (completed, interrupted, failed)
  - Accomplishments summary (agent-supplied free-form text describing what was done)
  - List of agents used (names, not prompts)
  - List of tools invoked (names, not arguments or output)
  - Context window usage (max depth reached, files touched)
- **Redaction**: Patterns applied to working directory path; secrets filtered via `redact_patterns`.
- **Size**: ~2–5 KB per session.

#### Level 3: Full
- **Source**: Level 2 + session-analyzer reports (from #729), tool_failures.jsonl, structured error logs
- **Captured**:
  - All of Level 2
  - Session-analyzer report (JSON): tool failure summaries, context depth analysis, agent decision rationale, code blocks processed
  - Tool error messages (structured, may include small code snippets)
  - Context-usage per tool (file counts, line ranges)
  - **Optionally** (when `consent_acknowledged: true`): raw prompt content, code snippets from tool inputs/outputs, full error traces
- **Redaction**: `redact_patterns` applied throughout; secrets must be redacted before spooling.
- **Size**: ~10–50 KB per session (full reports).
- **Consent gate**: Even if `log_drain.enabled: true` under the Duetto preset, level 3 NEVER ships unless `consent_acknowledged: true` is explicitly set in the project's `.claude-mpm/manifest.json` or user's local settings.

---

## Manifest Schema

The `log_drain` configuration lives at the **top level** of `.claude-mpm/manifest.json`. The schema is extensible (manifest allows `additionalProperties`), and an explicit schema entry should be added to `src/claude_mpm/manifest/schema.py` (referenced below).

### JSON Structure

```json
{
  "log_drain": {
    "enabled": false,
    "level": 1,
    "provider": "s3",
    "s3": {
      "bucket": "claude-mpm-logs-dev",
      "region": "us-west-2",
      "prefix": "claude-mpm/{project}/{user}/{date}",
      "aws_profile": null,
      "sse": "SSE-S3"
    },
    "flush_trigger": "session_end",
    "local_spool": true,
    "spool_max_mb": 50,
    "redact_patterns": [],
    "consent_acknowledged": false
  }
}
```

### Field Definitions

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Whether log-drain is active. Duetto preset sets to `true`. |
| `level` | int (0–3) | `1` | Payload granularity. Level 3 requires `consent_acknowledged: true`. |
| `provider` | string | `"s3"` | Backend provider. Currently only `"s3"` supported. |
| **`s3` object** | | |
| `s3.bucket` | string | — | S3 bucket name. **OPEN**: Duetto dev bucket TBD. |
| `s3.region` | string | — | AWS region (e.g., `"us-west-2"`). **OPEN**: Duetto region TBD. |
| `s3.prefix` | string | `"claude-mpm/{project}/{user}/{date}"` | S3 key prefix. Supports `{project}`, `{user}`, `{date}` (YYYY-MM-DD) placeholders. |
| `s3.aws_profile` | string? | `null` | Named AWS profile for credential resolution (SSO or profile chain). If null, uses default credential chain. |
| `s3.sse` | string | `"SSE-S3"` | Server-side encryption: `"SSE-S3"` or `"SSE-KMS"`. KMS recommended for level 3. |
| `flush_trigger` | string | `"session_end"` | When to flush spooled events. Currently only `"session_end"` (Stop hook). |
| `local_spool` | bool | `true` | Enable local JSONL spool (`~/.claude-mpm/drain/`) for durability and retry. |
| `spool_max_mb` | int | `50` | Max size of local spool (MB). Older entries evicted when exceeded. |
| `redact_patterns` | string[] | `[]` | Regex patterns to redact before spooling (e.g., `["\\b(password|token)\\b"]`). Applied to all payloads. |
| `consent_acknowledged` | bool | `false` | Required to ship level 3 (full content). When false, level 3 downgraded to level 2. |

### Manifest Integration

The `log_drain` block is a **top-level key** in `.claude-mpm/manifest.json`, on equal footing with `agents`, `hooks`, `settings`, and `setup`. During deep-merge:
- Repo manifest `log_drain` overrides preset `log_drain` (scalars and objects merged recursively).
- Arrays (`redact_patterns`) are replaced, not unioned.
- Presets (e.g., `claude-mpm-duetto`) can set defaults; repos and users can override locally.

**Schema entry** (to add to `src/claude_mpm/manifest/schema.py`):
```python
"log_drain": {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "enabled": {"type": "boolean", "default": False},
        "level": {"type": "integer", "minimum": 0, "maximum": 3, "default": 1},
        "provider": {"type": "string", "enum": ["s3"], "default": "s3"},
        "s3": {
            "type": "object",
            "properties": {
                "bucket": {"type": "string"},
                "region": {"type": "string"},
                "prefix": {"type": "string", "default": "claude-mpm/{project}/{user}/{date}"},
                "aws_profile": {"type": ["string", "null"], "default": None},
                "sse": {"type": "string", "enum": ["SSE-S3", "SSE-KMS"], "default": "SSE-S3"}
            }
        },
        "flush_trigger": {"type": "string", "enum": ["session_end"], "default": "session_end"},
        "local_spool": {"type": "boolean", "default": True},
        "spool_max_mb": {"type": "integer", "minimum": 1, "default": 50},
        "redact_patterns": {"type": "array", "items": {"type": "string"}, "default": []},
        "consent_acknowledged": {"type": "boolean", "default": False}
    }
}
```

### Duetto Preset

The `claude-mpm-duetto` package (a separate Python package registered under `claude_mpm.presets` entry-point group, per `src/claude_mpm/manifest/resolver.py`) ships a default manifest with:

```json
{
  "log_drain": {
    "enabled": true,
    "level": 1,
    "provider": "s3",
    "s3": {
      "bucket": "<TBD-duetto-dev-bucket>",
      "region": "<TBD>",
      "prefix": "claude-mpm/{project}/{user}/{date}",
      "aws_profile": null,
      "sse": "SSE-S3"
    },
    "flush_trigger": "session_end",
    "local_spool": true,
    "spool_max_mb": 50,
    "redact_patterns": [],
    "consent_acknowledged": false
  }
}
```

**Key points**:
- Duetto developers inherit `enabled: true` and `level: 1` by default.
- Individuals can disable by setting `log_drain.enabled: false` in local `.claude-mpm/manifest.json` or `.claude/settings.local.json`.
- To ship level 3, they must explicitly set `log_drain.consent_acknowledged: true` in their project or user manifest.
- Public/OSS default (no preset) is `enabled: false` and `level: 1`.

---

## Shipping Mechanism

### Local Spool (Durability & Retry)

**Location**: `~/.claude-mpm/drain/`

**Format**: JSONL (JSON Lines), one event per line. Structure:
```json
{
  "timestamp": "2026-06-10T18:42:00.123456Z",
  "session_id": "sess-abc123",
  "project": "claude-mpm",
  "user": "bob.matsuoka",
  "level": 1,
  "payload": {
    "tokens_in": 1234,
    "tokens_out": 567,
    "estimated_cost": 0.042,
    "model": "claude-haiku-4-5",
    "duration_sec": 42,
    "agents": ["engineer", "code-review"],
    "tools": ["Bash", "Read"],
    "error_codes": []
  }
}
```

**Lifecycle**:
1. **On-session events** (telemetry, resume-log snapshots): Appended to `~/.claude-mpm/drain/current.jsonl` as they occur.
2. **At session end** (Stop hook): Finalize current session events, flush to S3, and rotate spool file.
3. **Retention**: Keep spooled files for 7 days (or until successfully uploaded).
4. **Eviction**: If spool exceeds `spool_max_mb`, delete oldest files by date.
5. **Retry on startup**: On next session start, upload any pending spools (via a startup migration or service init hook).

### Batching & Flush at Stop Hook

**Trigger point**: The **Stop hook** handler (`src/claude_mpm/hooks/claude_hooks/handlers/stop_handler.py`, `handle_stop_fast()` function).

**Behavior**:
- Collects all telemetry + resume-log + session-analyzer output for the session.
- Serializes to JSONL and appends to local spool.
- **Immediately uploads to S3** if online and credentials available.
- On **network failure or missing credentials**: silently succeeds (fail-open); events remain in spool for retry next session.
- **Redaction**: Apply `redact_patterns` regex to all string fields before spooling.
- **Level downgrade**: If level=3 but `consent_acknowledged=false`, downgrade to level 2 before spooling.

**Timeout & safety**:
- Wrap S3 upload in `asyncio.wait_for(timeout=5.0)` to prevent Stop hook from hanging.
- Spool write is strictly local and immediate (no async waits).
- No hook failure propagation to the Stop event itself (fail-open semantics).

### Backoff & Retry

- **Failed uploads** are spooled locally and retried at next startup or on-demand via CLI command.
- **Exponential backoff**: On S3 errors, wait `min(2^attempt, 60)` seconds before retry.
- **Max retries**: 3 attempts per spool file before archiving to `~/.claude-mpm/drain/.failed/`.
- **Manual drain flush**: CLI command `claude-mpm drain flush` manually uploads pending spools and reports status.

### Offline No-Op

When offline (no network) or S3 bucket/credentials unavailable:
- Spool to local disk silently (no user-facing warnings).
- Log to `~/.claude-mpm/logs/` for diagnostic reference only.
- Attempt upload on next session start.
- If offline for extended periods, spool auto-evicts old entries (FIFO, respecting `spool_max_mb`).

---

## Authentication Model

### Credential Chain

Auth is handled by **boto3's default credential provider chain**:
1. **Environment variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` (not recommended for long-lived use).
2. **AWS SSO**: If `aws_profile` is set (or defaults to `default` profile), boto3 resolves SSO credentials via `~/.aws/config` and `~/.aws/sso/cache/`.
3. **EC2 instance profile / ECS role**: On Duetto CI/infra, auto-detected.
4. **Fallback**: If no credentials found, fail-open (silently skip upload, spool locally).

### Named Profile

```bash
# Configure SSO profile in ~/.aws/config
[profile duetto-dev]
sso_start_url = https://duetto.awsidentitycenter.com/...
sso_region = us-west-2
sso_account_id = 123456789012
sso_role_name = DevLogDrainAccess
region = us-west-2

# In manifest or settings
{
  "log_drain": {
    "s3": {
      "aws_profile": "duetto-dev"
    }
  }
}
```

### No Static Keys

- **Never store or ship AWS access keys** in manifest, settings, environment, or code.
- Rely exclusively on SSO or instance profiles.
- Credential expiry is handled by boto3; sessions auto-refresh.

---

## S3 Object Layout & Retention

### Key Format

```
s3://{bucket}/{prefix}/{session_id}.jsonl.gz
```

**Example**:
```
s3://claude-mpm-logs-dev/claude-mpm/bob.matsuoka/2026/06/10/sess-abc123.jsonl.gz
```

**Placeholders in `prefix`**:
- `{project}` → project name (from manifest or env)
- `{user}` → username (from shell `$USER` or AWS identity)
- `{date}` → `YYYY/MM/DD` (session start date, ISO format)

### Compression & Encryption

- **Compression**: gzip (`.jsonl.gz`), reducing 10–50 KB → 1–5 KB per session.
- **Server-side encryption**:
  - `SSE-S3` (AES-256, default): No key management overhead; suitable for telemetry/level 1–2.
  - `SSE-KMS` (recommended for level 3): Explicit key rotation, audit trail via CloudTrail.
- **Metadata**: Store session `level`, `timestamp`, `user` as S3 object tags for filtering.

### Lifecycle & Retention

- **Default**: Objects transition to **Glacier** after 90 days.
- **Purge**: Delete from Glacier after 1 year.
- **Rationale**: Long-term cost efficiency; keep level 3 data for learning/disputes, but avoid indefinite hot storage.
- **Configuration**: Managed via S3 lifecycle rule on the bucket (Duetto devops concern).

---

## Privacy & Redaction

### Opt-In for Content (Level 3)

- **Level 0–2** ship automatically when `enabled: true` (no prompt content, only metadata).
- **Level 3** (`full`) requires **explicit `consent_acknowledged: true`** in the manifest, even if `enabled: true`.
- If `consent_acknowledged: false` and `level: 3` is requested, silently downgrade to level 2.
- **Team communication**: Duetto team should inform developers that level 3 is opt-in and requires explicit consent.

### Redaction Patterns

Before spooling any event, apply user-supplied and default redaction patterns:

```python
default_patterns = [
    r'\b(password|passwd|pwd|secret|token|apikey|api_key|authorization)\s*[:=]\s*\S+',
    r'(\d{4}[-\s]?){3}\d{4}',  # Credit card
    r'Bearer\s+[A-Za-z0-9._\-]+',  # OAuth tokens
]

for pattern in redact_patterns + default_patterns:
    payload_str = re.sub(pattern, '[REDACTED]', payload_str, flags=re.IGNORECASE)
```

### Scrubbing Before Spool

- **Tool error output**: Truncate to first 200 chars; redact secrets.
- **Code snippets** (level 3): Redact comments and string literals that may contain secrets.
- **File paths**: Redact absolute paths; convert to relative or hash.
- **Git metadata**: Commit messages (may contain issue IDs, sensitive context) are captured as-is but redaction is applied.

---

## Reliability & Failure Handling

### Spool Durability

1. **Atomic writes**: Each event appended to spool atomically (open, write, close) to prevent partial records.
2. **Crash recovery**: On process restart, unpushed spools are automatically flushed.
3. **Disk full**: If `~/.claude-mpm/drain/` fills, evict oldest spool files (FIFO) until under `spool_max_mb`.
4. **Permissions**: Spool directory created with mode `0o700` (user-only); only the user can read.

### Max Spool Size Eviction

- **Check on startup** and before each append.
- **Sort by mtime**, delete oldest files until below threshold.
- **Log deletion** to `~/.claude-mpm/logs/drain.log` for transparency.

### Fail-Open Stop Hook

```python
async def handle_stop_fast() -> None:
    try:
        if not is_drain_enabled():
            return
        
        spool_event = build_spool_event()
        append_to_local_spool(spool_event)
        
        try:
            await asyncio.wait_for(upload_to_s3(spool_event), timeout=5.0)
        except (asyncio.TimeoutError, BotoError, FileNotFoundError):
            # Silently fail; event is in local spool for retry next session.
            pass
    except Exception:
        # Catch-all: never propagate to Stop event.
        # Log to diagnostic file only.
        pass
```

**Key semantics**:
- Stop hook always succeeds, regardless of drain state.
- Failures are logged but never surface to the user.
- Spool is the source of truth for durability; S3 is a best-effort async sink.

---

## Security Considerations

### Credential Handling

- ✅ **Use boto3's credential chain** (SSO, instance profiles, env vars via `AWS_*`).
- ✅ **Support named profiles** in `s3.aws_profile` for team SSO setup.
- ❌ **Never** store AWS access keys in manifest, settings, or code.
- ❌ **Never** log credential details, even at debug level.

### Spool Encryption at Rest

- Local spool (`~/.claude-mpm/drain/`) is **not encrypted** (lives on user's machine; file permissions provide access control).
- S3 objects are **always encrypted** (SSE-S3 by default; KMS for level 3).

### Content Sensitivity

- **Level 1–2**: No sensitive content (telemetry + metadata only).
- **Level 3**: May include prompts, code, errors → **require `consent_acknowledged: true`** and **enforce KMS encryption** (optional Duetto policy).

### No Secrets in Spool

Redaction patterns and user-supplied patterns must catch:
- AWS credentials, API keys, OAuth tokens
- Database passwords, connection strings
- PII: credit cards, SSNs, emails (context-dependent; not a blanket rule)

### Audit & Compliance

- **CloudTrail**: S3 access logged automatically; enables audit for level 3 access.
- **Lifecycle**: Glacier transition + purge after 1 year removes old logs; compliant with data retention policies.
- **Team oversight**: Duetto devops/security owns S3 bucket policy, encryption config, and access audits.

---

## Implementation Plan & Phasing

### Blocking Dependency

**Implementation is blocked until session-analyzer (#729) is merged.** The session-analyzer feature produces the prime level-2 and level-3 payloads (structured agent decision logs, tool failure summaries, context-usage analysis). Without it, log-drain has no meaningful content source beyond telemetry.

**Status**: #729 is merged. Implementation can proceed.

### Phase 1: Manifest Schema & Preset Package (Week 1)

1. **Add `log_drain` to manifest schema**: Update `src/claude_mpm/manifest/schema.py` with full schema above.
2. **Create `claude-mpm-duetto` preset package**:
   - New Python package (e.g., `claude-mpm-duetto` on GitHub + PyPI).
   - Registers entry point under `claude_mpm.presets` with name `"duetto"`.
   - Ships `manifest.json` with `log_drain.enabled: true, level: 1`.
3. **Update `manifest/resolver.py`**: Ensure preset resolution loads and deep-merges `log_drain` correctly.
4. **Tests**: Unit tests for schema validation and preset merging.

### Phase 2: Spool Service & Local Storage (Week 2)

1. **New module**: `src/claude_mpm/services/log_drain/`
   - `spool_manager.py`: JSONL append, local spool lifecycle (create, evict, list).
   - `s3_uploader.py`: boto3-based async uploader with backoff/retry.
   - `event_builder.py`: Construct spool events from telemetry, resume logs, session reports.
2. **Spool directory**: Create `~/.claude-mpm/drain/` with user-only permissions (0o700).
3. **Tests**: Local spool write/read, eviction, S3 upload mocks, fail-open behavior.

### Phase 3: Stop Hook Integration (Week 3)

1. **Update `src/claude_mpm/hooks/claude_hooks/handlers/stop_handler.py`**:
   - Call `log_drain.spool_and_flush()` in `handle_stop_fast()`.
   - Wrap in try-except to enforce fail-open semantics.
   - Add 5-second timeout on S3 upload via `asyncio.wait_for()`.
2. **Dependency injection**: Pass manifest config to Stop handler.
3. **Tests**: Integration tests with mock S3, offline scenarios, timeouts.

### Phase 4: CLI & User-Facing Features (Week 4)

1. **CLI commands**:
   - `claude-mpm drain status`: Show spool size, pending uploads, last flush time.
   - `claude-mpm drain flush`: Manually upload pending spools, report success/failure.
   - `claude-mpm manifest show log_drain`: Display resolved log-drain config.
2. **Error messaging**: User-friendly warnings for credential errors (only at startup).
3. **Logging**: Diagnostic log file `~/.claude-mpm/logs/drain.log` for troubleshooting.

### Phase 5: Optional Dependency & Release (Week 5)

1. **pyproject.toml**: Add optional extra `[drain]` that includes `boto3`.
   - Users opt into S3 capability: `pip install claude-mpm[drain]`.
   - Without the extra, log-drain gracefully disables (fail-open).
2. **Release**: Bump minor version (feature release).
3. **Documentation**: Add to user guide, reference docs, troubleshooting.
4. **Duetto rollout**: Deploy `claude-mpm-duetto` preset package; inform Duetto team.

### Code Touch-Points Summary

| Component | Files | Changes |
|-----------|-------|---------|
| **Manifest** | `src/claude_mpm/manifest/schema.py` | Add `log_drain` JSON schema |
| | `src/claude_mpm/manifest/resolver.py` | Ensure preset deep-merge works |
| **Preset** | `claude-mpm-duetto/` | New package with manifest.json |
| **Services** | `src/claude_mpm/services/log_drain/` | New module (spool_manager, s3_uploader, event_builder) |
| **Hooks** | `src/claude_mpm/hooks/claude_hooks/handlers/stop_handler.py` | Call drain.spool_and_flush() |
| **CLI** | `src/claude_mpm/cli/commands/drain.py` | New `drain` command group |
| **Build** | `pyproject.toml` | Add `[drain]` optional extra with boto3 |
| **Tests** | `tests/services/test_log_drain/` | Unit + integration tests |

---

## Open Questions for the Team

1. **Duetto S3 setup**:
   - What is the **dev bucket name** and **region** for Duetto's log-drain? (Placeholder: `claude-mpm-logs-dev`, `us-west-2`)
   - Should Duetto use **separate buckets** for level 1–2 (telemetry) vs. level 3 (full content)?

2. **AWS profile naming**:
   - What **SSO profile name** should Duetto developers use? (e.g., `duetto-dev`, `claude-dev`)
   - Should it be documented in `CONTRIBUTING.md` or an onboarding guide?

3. **Default redaction patterns**:
   - Beyond the standard set (passwords, tokens, credit cards), are there **project-specific patterns** to redact? (e.g., internal DNS names, customer names)
   - Should Duetto team maintain a curated list in the preset package?

4. **Default Duetto preset level**:
   - Should `claude-mpm-duetto` default to **level 1** (telemetry only, minimal data) or **level 2** (session summaries)?
   - **Rationale**: Level 1 is safer; level 2 enables team learning but captures more context.

5. **Spool retention**:
   - Should local spool files be **retained for 7 days** (default) or adjustable per user?
   - Should there be a **`claude-mpm drain purge`** command to manually delete old spools?

6. **Encryption for Duetto**:
   - Should Duetto enforce **SSE-KMS** for level 3 (via bucket policy)? Or leave as optional?
   - Which **KMS key** should be used? (Team-managed or account-wide default)

7. **Level 3 defaults**:
   - Should the Duetto preset default to `consent_acknowledged: false` (require explicit opt-in) or true (auto-send level 3)?
   - **Recommendation**: `false` (privacy-preserving, requires explicit consent).

---

## References

- **GitHub Issue #730**: Configurable cloud log-drain feature.
- **GitHub Issue #729** (merged): Session-analyzer — provides level 2–3 payload sources.
- **Related docs**:
  - `docs/design/manifest-config-system.md` — Manifest architecture & preset resolution.
  - `docs/developer/AGENT_ASSEMBLY_PIPELINE.md` — Session + agent context.
  - `docs/reference/cli-doctor.md` — Diagnostics; drain status can integrate here.

---

## Glossary

- **Spool**: Local JSONL file (`~/.claude-mpm/drain/`) buffering events for S3 upload.
- **Level**: Payload granularity (0–3); controls what data is captured.
- **Drain**: The log-drain service; spools and uploads session telemetry.
- **Flush**: Upload spooled events to S3 (triggered at Stop hook or on-demand).
- **Preset**: Named configuration package (e.g., `claude-mpm-duetto`) providing org defaults.
- **Redaction**: Regex-based scrubbing of secrets before spooling.
- **Consent**: User's explicit acknowledgment (`consent_acknowledged: true`) required for level 3.
- **Fail-open**: Drain failures never block Stop hook or user session.
