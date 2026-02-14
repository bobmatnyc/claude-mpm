# Devil's Advocate Verification Report

## Configuration Management UI for Claude MPM Dashboard

**Date**: 2026-02-13
**Branch**: `ui-agents-skills-config`
**Role**: Red Team / Devil's Advocate Verification
**Scope**: Post-implementation security, reliability, and edge case review

---

## Executive Summary

**Overall Risk Assessment: HIGH**

The implementation has made significant progress from the original risk assessment. File locking (ConfigFileLock) is properly integrated into mutation paths, the modular route architecture works well, and the backup/journal/verify pipeline for deployment operations is solid. However, this review identified **4 CRITICAL findings**, **5 HIGH findings**, and **7 MEDIUM findings** that require attention before this branch should be considered production-ready.

The two most serious issues are:
1. **Path traversal vulnerability in agent/skill deployment** -- attacker-controlled names are used directly in filesystem operations without sanitization (CRITICAL)
2. **CORS wildcard + no CSRF protection** -- any website in any browser tab can silently call mutation endpoints while the dashboard runs (CRITICAL when combined)

These are not theoretical risks. They are exploitable with trivial HTTP requests.

---

## Findings Summary

| Severity | Count | Key Areas |
|----------|-------|-----------|
| CRITICAL | 4 | Path traversal, CORS+CSRF, arbitrary file read |
| HIGH | 5 | Thread safety, singleton staleness, error info leakage |
| MEDIUM | 7 | No rate limiting, unbounded state, missing timeouts |
| LOW | 3 | Lock file cleanup, no audit trail, no operation cancellation |

---

## CRITICAL Findings

### C-01: Path Traversal in Agent Deployment (agent_name)

**File**: `src/claude_mpm/services/config_api/agent_deployment_handler.py:123-131`

**Description**: The `agent_name` parameter from the POST body is used directly to construct filesystem paths with zero validation:

```python
agent_name = body.get("agent_name", "").strip()  # line 123
agents_dir = Path.cwd() / ".claude" / "agents"
agent_path = agents_dir / f"{agent_name}.md"     # line 131
```

An attacker can send `{"agent_name": "../../.ssh/authorized_keys"}` which resolves to a path outside the agents directory. The `deploy_agent` function then writes content to this path.

Similarly, the DELETE endpoint at line 227 uses `request.match_info["agent_name"]` directly:
```python
agent_path = agents_dir / f"{agent_name}.md"  # line 239
agent_path.unlink()                            # line 265
```

**Impact**: Arbitrary file write (deploy) or arbitrary file deletion (undeploy) anywhere the server process has permissions.

**Reproduction**:
```bash
curl -X POST http://localhost:8765/api/config/agents/deploy \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "../../tmp/pwned"}'

curl -X DELETE http://localhost:8765/api/config/agents/../../etc/important.md
```

**Recommendation**: Add name format validation before ANY filesystem operation. Reject names containing `/`, `\`, `..`, or non-alphanumeric characters (except hyphens and underscores). Additionally, resolve the final path and verify it is still within `agents_dir`:

```python
import re
SAFE_NAME = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$')

if not SAFE_NAME.match(agent_name):
    return _error_response(400, "Invalid agent name", "VALIDATION_ERROR")

agent_path = (agents_dir / f"{agent_name}.md").resolve()
if not str(agent_path).startswith(str(agents_dir.resolve())):
    return _error_response(400, "Invalid agent name", "VALIDATION_ERROR")
```

**Severity**: CRITICAL
**Original Risk Assessment**: Not identified (this is a NEW finding)

---

### C-02: Path Traversal in Skill Deployment (skill_name)

**File**: `src/claude_mpm/services/config_api/skill_deployment_handler.py:137,244`

**Description**: Same pattern as C-01. `skill_name` from request body (deploy) or URL path (undeploy) is passed directly to service methods that construct filesystem paths without validation.

```python
skill_name = body.get("skill_name", "").strip()  # line 137
# ... passed to svc.deploy_skills(skill_names=[skill_name])
# ... and svc.remove_skills([skill_name])
```

The underlying `SkillsDeployerService` uses skill_name to construct paths in `~/.claude/skills/`. A malicious skill_name like `../../.bashrc` would write to or delete the user's shell configuration.

**Impact**: Arbitrary file write or deletion in the user's home directory.

**Reproduction**:
```bash
curl -X DELETE http://localhost:8765/api/config/skills/../../.bashrc
```

**Recommendation**: Apply the same SAFE_NAME validation as C-01 to ALL skill_name inputs before passing to service methods.

**Severity**: CRITICAL

---

### C-03: CORS Wildcard Enables Cross-Origin Attacks on Mutation Endpoints

**File**: `src/claude_mpm/services/monitor/server.py:305,314-325`

**Description**: The Socket.IO server and CORS middleware both use `cors_allowed_origins="*"`:

```python
self.sio = socketio.AsyncServer(cors_allowed_origins="*", ...)  # line 305

# CORS middleware
response.headers["Access-Control-Allow-Origin"] = "*"  # line 324
```

Combined with the lack of any CSRF protection (no tokens, no same-origin checks), this means **any website the user visits** can silently make authenticated requests to the dashboard API while it's running.

**Attack Scenario**:
1. User has dashboard running on `localhost:8765`
2. User visits `evil-site.com` in another tab
3. `evil-site.com` JavaScript sends: `fetch('http://localhost:8765/api/config/agents/deploy', {method:'POST', body:'{"agent_name":"malicious-agent"}'})`
4. The browser allows this because CORS says `*`
5. A malicious agent file is deployed to the user's project

This is NOT theoretical -- it is the standard CORS+CSRF attack vector.

**Impact**: Any website can deploy agents, undeploy agents, modify sources, trigger syncs, or switch deployment modes while the user's dashboard is running.

**Recommendation**:
1. Replace `cors_allowed_origins="*"` with explicit origins: `["http://localhost:8765", "http://127.0.0.1:8765"]` (or dynamically match the request origin against the server's own address)
2. Add a simple CSRF token mechanism: generate a token on page load, require it as a header (`X-CSRF-Token`) for all mutation requests
3. At minimum, add `SameSite=Strict` to any cookies and validate `Origin`/`Referer` headers on mutation endpoints

**Severity**: CRITICAL (when combined with mutation endpoints; would be MEDIUM for read-only)
**Original Risk Assessment**: Noted as "CORS: is '*' too permissive?" but dismissed as "localhost-only." The dismissal was incorrect -- CORS `*` on localhost is the exact attack vector used in real-world localhost CSRF exploits.

---

### C-04: Arbitrary File Read via Pre-Existing File Endpoints

**File**: `src/claude_mpm/services/monitor/server.py:712-786,900-1011`

**Description**: The `api_file_handler` (POST) and `api_file_read_handler` (GET) endpoints can read ANY file on the filesystem that the server process has permission to access. The only validation is:
```python
if not file_path or not Path(file_path).is_absolute():
    return ... "Invalid file path"
```

There is no restriction on WHICH absolute paths are valid. Any absolute path is accepted.

**Impact**: Combined with C-03 (CORS `*`), any website can read arbitrary files from the user's machine:
```javascript
// From evil-site.com:
fetch('http://localhost:8765/api/file/read?path=/etc/passwd')
  .then(r => r.json())
  .then(data => exfiltrate(data.content))
```

This can read SSH keys, environment files, credentials, database configs, etc.

**Note**: This is a pre-existing vulnerability, not introduced by the config UI work. However, it compounds with C-03.

**Recommendation**: Restrict file reads to the project working directory (Path.cwd()) and a whitelist of known config paths. Reject any path outside these boundaries.

**Severity**: CRITICAL (especially combined with C-03)

---

## HIGH Findings

### H-01: Thread-Unsafe Lazy Singleton Initialization

**Files**:
- `config_routes.py:25-85` (5 singletons)
- `agent_deployment_handler.py:33-76` (4 singletons)
- `skill_deployment_handler.py:26-68` (4 singletons)
- `autoconfig_handler.py:24-60` (3 singletons)

**Description**: All 16 lazy singletons use the non-thread-safe pattern:
```python
_agent_manager = None

def _get_agent_manager():
    global _agent_manager
    if _agent_manager is None:       # Thread A checks: None
        # Thread B also checks: None (race!)
        _agent_manager = AgentManager()  # Both threads create instances
    return _agent_manager
```

Since blocking service calls run in `asyncio.to_thread()`, multiple threads CAN execute these initialization blocks simultaneously. Two concurrent requests could each create a separate instance, with one being silently discarded.

**Impact**: Double initialization is wasteful but usually not harmful -- unless the services have stateful initialization (open file handles, caches, connections). More importantly, it violates the singleton guarantee that the code clearly intends.

**Recommendation**: Use `threading.Lock()` around initialization:
```python
_lock = threading.Lock()
def _get_agent_manager():
    global _agent_manager
    if _agent_manager is None:
        with _lock:
            if _agent_manager is None:  # double-check
                _agent_manager = AgentManager()
    return _agent_manager
```

**Severity**: HIGH
**Original Risk Assessment**: Identified as "Thread safety of lazy singleton dict" in scrutiny areas but not specifically assessed.

---

### H-02: Singletons Never Invalidated After Config Changes

**Files**: All singleton getters across config_routes.py, agent_deployment_handler.py, skill_deployment_handler.py

**Description**: Once initialized, singletons like `_agent_manager`, `_git_source_manager`, and `_skills_deployer` are NEVER invalidated. The ConfigFileWatcher correctly detects external changes and emits Socket.IO events, but the backend singletons that serve API data still hold references to stale configuration objects.

**Scenario**:
1. User opens dashboard, API initializes `_agent_manager` with current config
2. User runs `claude-mpm agents deploy new-agent` in CLI
3. ConfigFileWatcher detects mtime change, emits `external_change` event
4. Frontend receives event and re-fetches `/api/config/agents/deployed`
5. BUT `_agent_manager` still has its original state -- it may or may not reflect the CLI change depending on whether AgentManager re-reads from disk on each `list_agents()` call

**Impact**: Stale API responses after external (CLI) configuration changes. The severity depends on whether the underlying service objects re-read from disk on each call or cache internally.

**Recommendation**: Either:
1. Make singletons re-read from disk on each call (verify this is the current behavior)
2. Add singleton invalidation when ConfigFileWatcher detects changes
3. Or don't use singletons at all -- create fresh service instances per request (the cost is minimal for these objects)

**Severity**: HIGH

---

### H-03: Error Responses Leak Internal Details

**Files**: All handler files

**Description**: Every error handler returns `str(e)` as the error message:
```python
except Exception as e:
    return web.json_response(
        {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
        status=500,
    )
```

Python exception messages routinely contain:
- Full file paths (e.g., `FileNotFoundError: [Errno 2] No such file or directory: '/Users/masa/.claude-mpm/config/agent_sources.yaml'`)
- Stack traces (if the exception wraps another)
- Internal class names and module paths
- Database connection strings or API keys (in some error scenarios)

**Impact**: Information disclosure. Attackers learn the user's home directory, project structure, installed versions, and internal service architecture.

**Recommendation**: Log the full exception internally (`logger.error(...)` -- already done) but return only a sanitized message to the client. Create an error mapping:
```python
def _safe_error_message(e: Exception) -> str:
    if isinstance(e, FileNotFoundError):
        return "Configuration file not found"
    if isinstance(e, PermissionError):
        return "Permission denied"
    if isinstance(e, ConfigFileLockTimeout):
        return "Configuration file is locked by another process"
    return "Internal service error"
```

**Severity**: HIGH

---

### H-04: Agent Deployment Handler Does Not Use ConfigFileLock

**File**: `src/claude_mpm/services/config_api/agent_deployment_handler.py`

**Description**: Unlike the source management routes (config_sources.py) and the skill deployment handler (which uses `config_file_lock` on config writes), the agent deployment handler performs filesystem writes (creating/deleting `.md` files) WITHOUT acquiring any file lock.

```python
# agent_deployment_handler.py line 265
agent_path.unlink()  # No lock!

# agent_deployment_handler.py line 160-162
success = svc.deploy_agent(agent_name, agents_dir, force_rebuild=force)  # No lock!
```

While the `.claude/agents/` directory is different from config YAML files, concurrent deploy/undeploy of the same agent from two browser tabs or UI+CLI could cause:
- Partial writes (file being read while being written)
- Unlink of a file that was just deployed

**Impact**: Race condition between concurrent deploy and undeploy of the same agent. Could result in corrupted or missing agent files.

**Recommendation**: Add `config_file_lock()` around agent file operations, using the agent file path as the lock target.

**Severity**: HIGH
**Original Risk Assessment**: Risk C-5 "All config mutations unprotected" was identified as CRITICAL. While config_sources.py and skill_deployment_handler.py now use locks, agent_deployment_handler.py does NOT.

---

### H-05: Autoconfig Handler Accepts Arbitrary project_path

**File**: `src/claude_mpm/services/config_api/autoconfig_handler.py:190-197,228-236,267-275`

**Description**: All three autoconfig endpoints (`detect`, `preview`, `apply`) accept a `project_path` parameter from the request body and pass it directly to the toolchain analyzer:

```python
project_path = Path(body.get("project_path", str(Path.cwd())))
if not project_path.exists():
    return _error_response(400, ...)
# ... analyzer.analyze_toolchain(project_path)
```

The only validation is that the path exists. An attacker (via C-03 CORS vulnerability or a malicious browser extension) could:
1. Send `{"project_path": "/"}` to scan the entire filesystem
2. Send `{"project_path": "/etc"}` to discover system configuration
3. Send `{"project_path": "/home/other-user/project"}` to scan another user's project

The `apply` endpoint is even more dangerous -- it deploys agents relative to `Path.cwd()`, but the recommendations are generated from the attacker-controlled `project_path`.

**Impact**: Information disclosure about arbitrary directories. The `detect` and `preview` endpoints return detailed information about file contents, frameworks, and project structure.

**Recommendation**: Restrict `project_path` to `Path.cwd()` or its subdirectories. Better yet, remove the parameter entirely and always use `Path.cwd()`.

**Severity**: HIGH

---

## MEDIUM Findings

### M-01: No Rate Limiting on Any Endpoints

**Description**: There is no rate limiting on any API endpoint. The sync endpoints (`POST /api/config/sources/{type}/sync`) spawn asyncio tasks. The deploy endpoints create backup files. The autoconfig endpoints run potentially expensive toolchain analysis.

**Impact**: A rogue script or CORS attack could:
- Spawn hundreds of concurrent sync tasks consuming all available Git bandwidth
- Fill disk with backup files
- CPU-starve the server with toolchain analysis requests

**Recommendation**: Add basic rate limiting middleware. Even a simple counter (e.g., 10 mutations per minute, 3 concurrent sync operations) would prevent abuse.

**Severity**: MEDIUM

---

### M-02: sync_status Dict Grows Without Bound

**File**: `src/claude_mpm/services/monitor/routes/config_sources.py:44`

**Description**: `sync_status: Dict[str, Dict[str, Any]] = {}` accumulates entries for every sync job. The `last_results` sub-dict also grows with each source synced. There is no pruning mechanism.

**Impact**: Memory leak over long server uptime. Each sync adds ~200 bytes. After thousands of syncs over weeks, this becomes measurable.

**Recommendation**: Add a TTL or max-entry limit. Keep only the last 100 sync results.

**Severity**: MEDIUM

---

### M-03: active_sync_tasks and _active_jobs Accessed Unsafely

**Files**:
- `config_sources.py:43` -- `active_sync_tasks: Dict[str, asyncio.Task]`
- `autoconfig_handler.py:29` -- `_active_jobs: Dict[str, asyncio.Task]`

**Description**: These dicts are accessed from the asyncio event loop (in route handlers) AND from background tasks (via `asyncio.create_task`). While asyncio tasks run cooperatively in the same thread, the `_sync_source_blocking` function runs in a thread pool via `asyncio.to_thread()`. If a thread pool worker accesses these dicts while the event loop is also accessing them, there is a potential race.

In practice, the dicts are only modified in `finally` blocks of async functions (not in thread pool workers), so the current code is likely safe. But this is fragile -- one refactor could introduce a race.

**Recommendation**: Document the threading model. Consider using `asyncio.Lock()` for explicit safety.

**Severity**: MEDIUM

---

### M-04: No Background Task Timeout

**Files**: `config_sources.py:707-770`, `autoconfig_handler.py:349-544`

**Description**: Background sync and autoconfig tasks have no timeout. If a Git clone hangs (network issues, massive repo), the sync task runs indefinitely. The `active_sync_tasks` dict holds a reference to the task forever.

**Impact**: Hung tasks consume resources. The "sync in progress" check (line 587-593) prevents new syncs for the same source, so a hung sync permanently blocks future syncs for that source until server restart.

**Recommendation**: Add `asyncio.wait_for()` with a configurable timeout (e.g., 120s for sync, 300s for autoconfig).

**Severity**: MEDIUM

---

### M-05: No Backup Pruning Strategy

**File**: `src/claude_mpm/services/config_api/backup_manager.py` (referenced but not directly inspected in detail)

**Description**: `BackupManager.create_backup()` is called on every deploy, undeploy, mode switch, and autoconfig apply. Each backup presumably copies files. There is no visible cleanup/pruning mechanism.

**Impact**: Disk space consumption grows with every mutation. A user who deploys/undeploys 50 agents will have 50 backup directories.

**Recommendation**: Add automatic pruning: keep the last N backups (e.g., 20) or backups from the last 7 days.

**Severity**: MEDIUM

---

### M-06: Config File Watcher Doesn't Watch Project-Level Config

**File**: `src/claude_mpm/services/monitor/handlers/config_handler.py:98-105`

**Description**: The watcher monitors:
```python
home / ".claude-mpm" / "config" / "agent_sources.yaml"
home / ".claude-mpm" / "config" / "skill_sources.yaml"
home / ".claude-mpm" / "configuration.yaml"
```

But skill_deployment_handler writes to:
```python
Path.cwd() / ".claude-mpm" / "configuration.yaml"  # Project-level, not home-level
```

The watcher watches `~/.claude-mpm/configuration.yaml` (home level), but the deployment handler writes to `$CWD/.claude-mpm/configuration.yaml` (project level). These are different files unless CWD is the user's home directory.

**Impact**: Mode switch changes and user_defined skill list modifications via CLI won't be detected by the file watcher, so the frontend won't refresh.

**Recommendation**: Add `Path.cwd() / ".claude-mpm" / "configuration.yaml"` to the watched files list, or dynamically determine which config paths are active.

**Severity**: MEDIUM

---

### M-07: Batch Deploy Creates One AgentDeploymentService Per Iteration

**File**: `agent_deployment_handler.py:334-341`

**Description**: In `deploy_collection`, the `_deploy_one` closure calls `_get_agent_deployment_service()` on every iteration. Since it's a singleton, this is fine. But it ALSO calls `_get_backup_manager()`, `_get_operation_journal()`, and `_get_deployment_verifier()` on every iteration via thread pool, triggering thread-unsafe singleton checks (H-01) N times.

Additionally, each deployment iteration creates a SEPARATE backup. For a batch of 20 agents, this creates 20 separate backup entries rather than one batch backup.

**Impact**: Excessive backup creation. Potential thread-safety issues during batch operations.

**Recommendation**: Create a single batch backup before the loop. Move singleton acquisition outside the per-item closure.

**Severity**: MEDIUM

---

## LOW Findings

### L-01: Lock Files Persist After Use

**File**: `src/claude_mpm/core/config_file_lock.py:67`

**Description**: Lock files (`*.yaml.lock`) are created but never deleted. `fcntl.flock(LOCK_UN)` releases the lock but doesn't remove the file.

**Impact**: Cosmetic -- `.lock` files accumulate in the config directory. No functional impact since flock is on the file descriptor, not file existence.

**Recommendation**: Consider deleting lock files on release (with a try/except for race conditions) or document that they are expected.

---

### L-02: No Operation Cancellation Mechanism

**Description**: Once a sync-all or autoconfig job starts, there is no way to cancel it. No cancel endpoint exists, and the background tasks don't check for cancellation signals.

**Recommendation**: Add `GET /api/config/operations/{job_id}/cancel` that sets a cancellation flag checked by the background task.

---

### L-03: No Persistent Audit Trail

**Description**: The OperationJournal tracks operations during server runtime, but there's no persistent audit log that survives server restarts. A user cannot answer "who deployed agent X and when?" after a server restart.

**Recommendation**: Append-only audit log file (e.g., `~/.claude-mpm/audit.log`) with timestamped entries for all mutation operations.

---

## Comparison with Original Risk Assessment

### Risks Addressed

| Original Risk | Status | Evidence |
|---------------|--------|----------|
| C-1: Lost config updates | **Mitigated** | ConfigFileLock used in config_sources.py and skill_deployment_handler.py |
| C-2: TOCTOU race | **Mitigated** | Read-modify-write happens inside lock context |
| C-5: All mutations unprotected | **Partially mitigated** | Sources and skill config use locks; agent deployment does NOT (see H-04) |
| C-8: Valid path whitelisting | **Mitigated** | Source routes validate URLs against GITHUB_URL_PATTERN |
| ST-1: Stale dashboard | **Mitigated** | ConfigFileWatcher polls every 5s, emits Socket.IO events |
| ST-2: Socket.IO disconnect | **Mitigated** | sync-status polling endpoint exists as fallback |
| O-1: Partial sync | **Mitigated** | sync-all continues on individual failure |
| O-2: Partial deploy | **Mitigated** | Backup-journal-verify pipeline implemented |
| O-4: Orphaned agents on source removal | **Partially mitigated** | Endpoint returns `orphaned_items: []` but doesn't actually check |
| O-5: Core skills appear removable | **Mitigated** | `_get_immutable_skills()` check in undeploy handler |
| P-1: Large agent lists | **Mitigated** | Pagination implemented via paginate() utility |

### Risks NOT Addressed (Still Open)

| Original Risk | Status | Notes |
|---------------|--------|-------|
| C-3: Multi-tab consistency | **Open** | No mechanism prevents mutations from concurrent browser tabs |
| C-4: Stale agents in Claude sessions | **Mitigated** | Session detector warns about active sessions |
| C-6: Env var override visibility | **Open** | UI shows file values only; env var overrides not surfaced |
| C-7: Dual config system | **Open** | Pydantic vs YAML drift not addressed |
| ST-3: Server restart mid-operation | **Partially addressed** | Journal exists but no startup recovery check |
| O-3: Auto-configure overwrites | **Mitigated** | Preview + confirm two-step flow implemented |
| P-2: Large repo sync timeout | **Open** | No timeout on sync operations (see M-04) |
| UX-2: Mode switching data loss | **Mitigated** | EMPTY_SKILL_LIST guard implemented |

### NEW Risks Not in Original Assessment

| New Risk | Severity | Notes |
|----------|----------|-------|
| C-01: Path traversal (agent) | **CRITICAL** | Not previously identified |
| C-02: Path traversal (skill) | **CRITICAL** | Not previously identified |
| C-03: CORS+CSRF attack | **CRITICAL** | Previously dismissed as low-risk |
| H-01: Thread-unsafe singletons | **HIGH** | Not previously identified |
| H-05: Arbitrary project_path | **HIGH** | Not previously identified |
| M-06: Watcher misses project config | **MEDIUM** | Not previously identified |

---

## Priority-Ordered Action Items

### Immediate (Before Merge)

1. **[CRITICAL] Add name sanitization to agent_name and skill_name** in all deployment handlers. Reject any name containing `/`, `\`, `..`, or characters outside `[a-zA-Z0-9_-]`. Verify resolved path is within expected directory.

2. **[CRITICAL] Restrict CORS origins** from `*` to the server's own address. At minimum, validate `Origin` header on mutation requests.

3. **[CRITICAL] Restrict file read endpoints** to project directory and known config paths. Block reading outside `Path.cwd()` and `~/.claude-mpm/`.

4. **[HIGH] Remove project_path parameter** from autoconfig endpoints. Always use `Path.cwd()`.

5. **[HIGH] Add ConfigFileLock to agent deployment** handler's file operations.

### Short-Term (Before Phase 3 GA)

6. **[HIGH] Fix thread-safe singleton initialization** with double-check locking.

7. **[HIGH] Sanitize error messages** -- don't return raw `str(e)` to clients.

8. **[MEDIUM] Add operation timeouts** to sync and autoconfig background tasks.

9. **[MEDIUM] Fix config file watcher** to include project-level configuration.yaml.

10. **[MEDIUM] Add backup pruning** strategy.

### Medium-Term

11. **[MEDIUM] Add rate limiting** to mutation endpoints.

12. **[MEDIUM] Implement sync_status pruning** to prevent memory growth.

13. **[MEDIUM] Create single batch backup** for deploy-collection instead of per-agent.

14. **[LOW] Add operation cancellation** endpoint for long-running tasks.

15. **[LOW] Add persistent audit log** for mutation operations.

---

## Test Coverage Assessment

### What IS Tested

| Area | File | Coverage |
|------|------|----------|
| Phase 1 read-only endpoints | `tests/test_config_routes.py` | Good: happy path, error path, empty state for all 6 endpoints |
| Source management routes | `tests/unit/services/monitor/routes/test_config_sources.py` | Good: add, remove, update, sync, protected sources |
| Deployment business rules | `tests/test_config_api_business_rules.py` | Good: core agent/skill protection, mode switch validation |
| Deployment operations | `tests/test_config_api_deployment.py` | Moderate: deploy, undeploy, batch, skill deploy |
| Config file lock | `tests/unit/core/test_config_file_lock.py` | Present (not reviewed in detail) |
| Config validation | `tests/dashboard/test_config_validate.py` | Present |
| Skill links | `tests/dashboard/test_config_skill_links.py` | Present |

### What is NOT Tested

| Gap | Risk Level | Notes |
|-----|-----------|-------|
| Path traversal attacks | **CRITICAL** | No test sends `../` in agent_name or skill_name |
| Concurrent access | **HIGH** | No tests for simultaneous deploy + undeploy |
| CORS behavior | **HIGH** | No test verifies cross-origin requests are blocked |
| Frontend components | **HIGH** | Zero test files in dashboard-svelte/src/ (confirmed) |
| Error message content | **MEDIUM** | No test verifies error responses don't leak paths |
| Timeout behavior | **MEDIUM** | No test for sync/autoconfig timeout |
| Lock contention under load | **MEDIUM** | No test with multiple threads competing for locks |
| Autoconfig with malicious project_path | **HIGH** | No test for path restriction |
| Config file watcher | **MEDIUM** | No test verifies watcher emits events on file changes |
| Singleton thread safety | **MEDIUM** | No concurrent initialization test |

### Recommendation: Add These Test Cases Immediately

```python
# test_security.py - Add before merge

def test_agent_name_path_traversal():
    """Agent name with ../ should be rejected."""
    resp = client.post("/api/config/agents/deploy",
                       json={"agent_name": "../../etc/passwd"})
    assert resp.status == 400

def test_skill_name_path_traversal():
    """Skill name with ../ should be rejected."""
    resp = client.delete("/api/config/skills/../../.bashrc")
    assert resp.status == 400

def test_agent_name_special_chars():
    """Agent names with special chars should be rejected."""
    for bad_name in ["foo/bar", "foo\\bar", "foo..bar", "../evil", ""]:
        resp = client.post("/api/config/agents/deploy",
                           json={"agent_name": bad_name})
        assert resp.status == 400, f"Name '{bad_name}' should be rejected"

def test_error_responses_no_path_leak():
    """Error responses should not contain filesystem paths."""
    resp = client.get("/api/config/project/summary")  # with broken service
    data = resp.json()
    if not data["success"]:
        assert "/Users/" not in data.get("error", "")
        assert "/home/" not in data.get("error", "")
```

---

## Final Assessment

The implementation is structurally sound: modular routes, proper async wrapping, file locking on most write paths, pagination, backup/journal/verify pipeline, and reasonable test coverage for business logic. The original risk assessment was thorough and most of its high-priority recommendations were followed.

However, the **security posture is insufficient for a system that writes to the filesystem**. The path traversal vulnerabilities (C-01, C-02) and CORS misconfiguration (C-03) are exploitable with trivial HTTP requests. These must be fixed before the branch merges.

The good news: all critical findings have straightforward fixes (input validation, CORS restriction, path sandboxing). None require architectural changes. A focused effort of 1-2 days addresses all critical and high findings.

**Bottom line**: Fix C-01 through C-04 and H-04 through H-05 before merge. The rest can be addressed incrementally.
