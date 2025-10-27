# Local Operations CLI Commands Reference

Complete reference documentation for all `local-deploy` CLI commands with examples, options, return codes, and configuration details.

## Table of Contents

- [Command Overview](#command-overview)
- [Global Concepts](#global-concepts)
- [Command Reference](#command-reference)
  - [start](#start)
  - [stop](#stop)
  - [restart](#restart)
  - [status](#status)
  - [health](#health)
  - [list](#list)
  - [monitor](#monitor)
  - [history](#history)
  - [enable-auto-restart](#enable-auto-restart)
  - [disable-auto-restart](#disable-auto-restart)
- [Configuration File Reference](#configuration-file-reference)
- [Return Codes](#return-codes)
- [Examples](#examples)

## Command Overview

The `local-deploy` command provides comprehensive process management for local development deployments:

```bash
claude-mpm local-deploy <subcommand> [options]
```

### Available Subcommands

| Command | Purpose | Typical Use Case |
|---------|---------|------------------|
| `start` | Start new deployment | Launch development server with monitoring |
| `stop` | Stop deployment | Shutdown server gracefully |
| `restart` | Restart deployment | Apply configuration changes |
| `status` | Show comprehensive status | Debugging and diagnostics |
| `health` | Show health check results | Verify deployment health |
| `list` | List all deployments | See running/stopped deployments |
| `monitor` | Live monitoring dashboard | Watch metrics in real-time |
| `history` | Show restart history | Diagnose stability issues |
| `enable-auto-restart` | Enable auto-restart | Add crash recovery to deployment |
| `disable-auto-restart` | Disable auto-restart | Remove crash recovery |

## Global Concepts

### Deployment ID

Every deployment is assigned a unique identifier:
- Format: `deployment-<timestamp>-<random>`
- Example: `deployment-20251022-a3f7b2c1`
- Used to reference deployment in all commands
- Returned by `start` command
- Listed by `list` command

### Process Status

Deployments can be in one of several states:

| Status | Meaning | Next Steps |
|--------|---------|------------|
| `RUNNING` | Process running normally | Monitor, check health |
| `STOPPED` | Gracefully stopped | Restart if needed |
| `CRASHED` | Process crashed/exited | Check logs, review restart history |
| `STARTING` | Process starting up | Wait for startup, then verify |
| `STOPPING` | Graceful shutdown in progress | Wait for completion |

### Health Status

Health checks aggregate into overall status:

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| `HEALTHY` | All checks passing | None - operating normally |
| `DEGRADED` | Some issues detected | Investigate non-critical issues |
| `UNHEALTHY` | Critical issues | Immediate attention required |
| `UNKNOWN` | Unable to determine | Check process status, restart monitoring |

## Command Reference

### start

Start a new local deployment with process monitoring.

**Synopsis:**
```bash
claude-mpm local-deploy start --command <cmd> [options]
```

**Required Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `--command`, `-c` | string | Command to execute (e.g., "npm run dev") |

**Optional Arguments:**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--working-directory`, `-d` | path | current dir | Working directory for process |
| `--port`, `-p` | integer | none | Port number for deployment |
| `--auto-find-port` | flag | true | Auto-find alternative port if unavailable |
| `--no-auto-find-port` | flag | false | Disable automatic port finding |
| `--auto-restart` | flag | false | Enable automatic restart on crashes |
| `--log-file` | path | none | Path to log file for error monitoring |
| `--env`, `-e` | KEY=VALUE | none | Environment variable (repeatable) |

**Output:**

```
Deployment Started
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Deployment ID: deployment-20251022-a3f7b2c1┃
┃ Command:       npm run dev                  ┃
┃ PID:           12345                        ┃
┃ Port:          3000                         ┃
┃ Auto-Restart:  Enabled                      ┃
┃ Status:        RUNNING                      ┃
┃ Health:        HEALTHY                      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

URL: http://localhost:3000
```

**Examples:**

```bash
# Basic Next.js deployment
claude-mpm local-deploy start --command "npm run dev" --port 3000

# With auto-restart and log monitoring
claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --auto-restart \
  --log-file ./logs/nextjs.log

# Django with environment variables
claude-mpm local-deploy start \
  --command "python manage.py runserver 8000" \
  --port 8000 \
  --auto-restart \
  --env DJANGO_DEBUG=True \
  --env DATABASE_URL=postgresql://localhost/dev

# Custom working directory
claude-mpm local-deploy start \
  --command "npm start" \
  --working-directory /path/to/project \
  --port 3000 \
  --auto-find-port

# Without auto-find-port (strict port requirement)
claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --no-auto-find-port
```

**Return Codes:**
- `0`: Success - deployment started
- `1`: Error - command execution failed
- `2`: Error - port unavailable (with --no-auto-find-port)
- `3`: Error - invalid arguments

---

### stop

Stop a running deployment with graceful shutdown.

**Synopsis:**
```bash
claude-mpm local-deploy stop <deployment-id> [options]
```

**Required Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `deployment-id` | string | Deployment ID to stop |

**Optional Arguments:**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--timeout`, `-t` | integer | 10 | Timeout in seconds for graceful shutdown |
| `--force`, `-f` | flag | false | Force kill immediately (SIGKILL) |

**Behavior:**

1. **Graceful Shutdown (Default)**:
   - Sends SIGTERM to process
   - Waits for timeout period
   - Process can clean up resources
   - If timeout expires, sends SIGKILL

2. **Force Shutdown (--force)**:
   - Sends SIGKILL immediately
   - No cleanup opportunity
   - Use for hung processes

**Output:**

```
Stopping deployment-20251022-a3f7b2c1...
✓ Process stopped gracefully (PID: 12345)
✓ Auto-restart disabled
✓ State cleaned up
```

**Examples:**

```bash
# Graceful stop with default timeout (10s)
claude-mpm local-deploy stop deployment-20251022-a3f7b2c1

# Custom timeout
claude-mpm local-deploy stop deployment-20251022-a3f7b2c1 --timeout 30

# Force kill immediately
claude-mpm local-deploy stop deployment-20251022-a3f7b2c1 --force

# Force kill hung process
claude-mpm local-deploy stop deployment-20251022-a3f7b2c1 --force --timeout 0
```

**Return Codes:**
- `0`: Success - deployment stopped
- `1`: Error - deployment not found
- `2`: Error - process did not stop within timeout
- `130`: Interrupted by user (Ctrl+C)

---

### restart

Restart a deployment with the same configuration.

**Synopsis:**
```bash
claude-mpm local-deploy restart <deployment-id> [options]
```

**Required Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `deployment-id` | string | Deployment ID to restart |

**Optional Arguments:**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--timeout`, `-t` | integer | 10 | Timeout in seconds for graceful shutdown |

**Behavior:**

1. Stops the process gracefully
2. Waits for complete shutdown
3. Restarts with original configuration
4. Preserves auto-restart setting
5. Maintains deployment ID

**Output:**

```
Restarting deployment-20251022-a3f7b2c1...
✓ Process stopped (PID: 12345)
✓ Process started (PID: 12789)
✓ Health check: HEALTHY

Deployment Restarted
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Deployment ID: deployment-20251022-a3f7b2c1┃
┃ New PID:       12789                        ┃
┃ Status:        RUNNING                      ┃
┃ Health:        HEALTHY                      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Examples:**

```bash
# Basic restart
claude-mpm local-deploy restart deployment-20251022-a3f7b2c1

# With custom shutdown timeout
claude-mpm local-deploy restart deployment-20251022-a3f7b2c1 --timeout 30
```

**Return Codes:**
- `0`: Success - deployment restarted
- `1`: Error - deployment not found
- `2`: Error - stop failed
- `3`: Error - start failed

---

### status

Show comprehensive deployment status including process info, health, and restart history.

**Synopsis:**
```bash
claude-mpm local-deploy status <deployment-id> [options]
```

**Required Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `deployment-id` | string | Deployment ID to check |

**Optional Arguments:**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--json` | flag | false | Output in JSON format for scripting |

**Output (Text Format):**

```
Deployment Status: deployment-20251022-a3f7b2c1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Process Information
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field            ┃ Value                    ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ PID              │ 12345                    │
│ Status           │ RUNNING                  │
│ Uptime           │ 2h 34m 12s               │
│ Command          │ npm run dev              │
│ Port             │ 3000                     │
│ CPU              │ 2.3%                     │
│ Memory           │ 245 MB                   │
└──────────────────┴──────────────────────────┘

Health Status
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Overall          ┃ HEALTHY                  ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ HTTP Check       │ ✓ HEALTHY (143ms)        │
│ Process Check    │ ✓ HEALTHY                │
│ Resource Check   │ ✓ HEALTHY                │
└──────────────────┴──────────────────────────┘

Auto-Restart Configuration
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Enabled          ┃ Yes                      ┃
┃ Total Restarts   ┃ 2                        ┃
┃ Successful       ┃ 2                        ┃
┃ Failed           ┃ 0                        ┃
┃ Circuit Breaker  ┃ CLOSED                   ┃
└──────────────────┴──────────────────────────┘

Memory Trend
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Current          ┃ 245 MB                   ┃
┃ Growth Rate      ┃ +0.5 MB/min              ┃
┃ Leak Detected    ┃ No                       ┃
└──────────────────┴──────────────────────────┘
```

**Output (JSON Format):**

```json
{
  "deployment_id": "deployment-20251022-a3f7b2c1",
  "process": {
    "pid": 12345,
    "status": "RUNNING",
    "uptime_seconds": 9252,
    "command": "npm run dev",
    "port": 3000,
    "cpu_percent": 2.3,
    "memory_mb": 245.7,
    "start_time": 1729612800.0
  },
  "health": {
    "overall_status": "HEALTHY",
    "checks": [
      {
        "type": "http",
        "status": "HEALTHY",
        "message": "HTTP 200 OK",
        "response_time_ms": 143
      },
      {
        "type": "process",
        "status": "HEALTHY",
        "message": "Process running and responsive"
      },
      {
        "type": "resource",
        "status": "HEALTHY",
        "message": "All resources within limits"
      }
    ],
    "last_check": 1729622052.0
  },
  "restart_history": {
    "total_restarts": 2,
    "successful_restarts": 2,
    "failed_restarts": 0,
    "circuit_breaker_state": "CLOSED",
    "recent_attempts": []
  },
  "memory_trend": {
    "current_mb": 245.7,
    "growth_rate_mb_per_minute": 0.5,
    "leak_detected": false
  },
  "resource_status": {
    "issues": [],
    "critical": false
  },
  "log_errors": []
}
```

**Examples:**

```bash
# Text output (human-readable)
claude-mpm local-deploy status deployment-20251022-a3f7b2c1

# JSON output (for scripting)
claude-mpm local-deploy status deployment-20251022-a3f7b2c1 --json

# JSON output to file
claude-mpm local-deploy status deployment-20251022-a3f7b2c1 --json > status.json

# Check status in script
STATUS=$(claude-mpm local-deploy status deployment-20251022-a3f7b2c1 --json)
HEALTH=$(echo $STATUS | jq -r '.health.overall_status')
if [ "$HEALTH" != "HEALTHY" ]; then
  echo "Deployment unhealthy!"
fi
```

**Return Codes:**
- `0`: Success - status retrieved
- `1`: Error - deployment not found
- `2`: Error - unable to get process info

---

### health

Show health check status for a deployment.

**Synopsis:**
```bash
claude-mpm local-deploy health <deployment-id>
```

**Required Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `deployment-id` | string | Deployment ID to check |

**Output:**

```
Health Status: deployment-20251022-a3f7b2c1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall Health: HEALTHY

Individual Checks
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check Type      ┃ Status    ┃ Details                       ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ HTTP            │ ✓ HEALTHY │ HTTP 200 OK (143ms)           │
│ Process         │ ✓ HEALTHY │ Running and responsive        │
│ Resource        │ ✓ HEALTHY │ CPU: 2.3%, Memory: 245MB      │
└─────────────────┴───────────┴───────────────────────────────┘

Last Check: 2025-10-22 15:30:45
Next Check: 2025-10-22 15:31:15 (in 28 seconds)
```

**Health Status Meanings:**

| Status | Symbol | Meaning |
|--------|--------|---------|
| HEALTHY | ✓ | All checks passing |
| DEGRADED | ⚠ | Some issues, non-critical |
| UNHEALTHY | ✗ | Critical issues detected |
| UNKNOWN | ? | Unable to determine |

**Examples:**

```bash
# Check health
claude-mpm local-deploy health deployment-20251022-a3f7b2c1

# Watch health status
watch -n 5 'claude-mpm local-deploy health deployment-20251022-a3f7b2c1'
```

**Return Codes:**
- `0`: Success - deployment healthy or degraded
- `1`: Error - deployment not found
- `2`: Error - deployment unhealthy
- `3`: Error - health status unknown

---

### list

List all deployments with status information.

**Synopsis:**
```bash
claude-mpm local-deploy list [options]
```

**Optional Arguments:**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--status` | string | none | Filter by status (running/stopped/crashed) |

**Output:**

```
Local Deployments
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Deployment ID              ┃ PID   ┃ Port  ┃ Status   ┃ Health     ┃ Uptime   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━┩
│ deployment-20251022-a3f7b2 │ 12345 │ 3000  │ RUNNING  │ ✓ HEALTHY  │ 2h 34m   │
│ deployment-20251022-b8c3e4 │ 12389 │ 8000  │ RUNNING  │ ⚠ DEGRADED │ 1h 12m   │
│ deployment-20251021-f4d9a1 │ -     │ 8080  │ STOPPED  │ -          │ -        │
└────────────────────────────┴───────┴───────┴──────────┴────────────┴──────────┘

Total: 3 deployments (2 running, 1 stopped)
```

**Examples:**

```bash
# List all deployments
claude-mpm local-deploy list

# List only running deployments
claude-mpm local-deploy list --status running

# List only stopped deployments
claude-mpm local-deploy list --status stopped

# List only crashed deployments
claude-mpm local-deploy list --status crashed
```

**Return Codes:**
- `0`: Success - deployments listed
- `1`: Error - unable to read deployment state

---

### monitor

Live monitoring dashboard with real-time updates.

**Synopsis:**
```bash
claude-mpm local-deploy monitor <deployment-id> [options]
```

**Required Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `deployment-id` | string | Deployment ID to monitor |

**Optional Arguments:**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--refresh` | integer | 2 | Refresh interval in seconds |

**Display:**

```
Monitoring: deployment-20251022-a3f7b2c1         [Refresh: 2s] [Press Ctrl+C to exit]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Process Metrics                           Health Status
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓           ┏━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Metric      ┃ Value        ┃           ┃ Check       ┃ Status     ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩           ┡━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ PID         │ 12345        │           │ Overall     │ ✓ HEALTHY  │
│ Status      │ RUNNING      │           │ HTTP        │ ✓ HEALTHY  │
│ Uptime      │ 2h 34m 23s   │           │ Process     │ ✓ HEALTHY  │
│ CPU         │ ▇▇▇░░ 2.3%   │           │ Resource    │ ✓ HEALTHY  │
│ Memory      │ ▇▇▇▇░ 245 MB │           └─────────────┴────────────┘
│ Threads     │ 12           │
│ Connections │ 5            │           Auto-Restart: Enabled
└─────────────┴──────────────┘           Circuit Breaker: CLOSED

CPU History (last 30s)                    Memory History (last 5m)
 5% ┤      ╭─╮                             300MB ┤
 4% ┤   ╭──╯ ╰─╮                           250MB ┼───────────────────
 3% ┼───╯      ╰──╮                        200MB ┤
 2% ┤             ╰─                       150MB ┤
 1% ┤                                      100MB ┤
 0% ┴─────────────────→                     50MB ┤
                                              0MB ┴────────────────→

Recent Events
• 15:30:45 - Health check: HEALTHY
• 15:30:15 - Health check: HEALTHY
• 15:29:45 - Health check: HEALTHY

Last Updated: 2025-10-22 15:30:58
```

**Features:**
- Real-time metric updates
- ASCII graphs for CPU and memory trends
- Health status monitoring
- Event log streaming
- Auto-refresh with configurable interval

**Examples:**

```bash
# Monitor with default 2-second refresh
claude-mpm local-deploy monitor deployment-20251022-a3f7b2c1

# Monitor with 5-second refresh
claude-mpm local-deploy monitor deployment-20251022-a3f7b2c1 --refresh 5

# Monitor with 1-second refresh (fast)
claude-mpm local-deploy monitor deployment-20251022-a3f7b2c1 --refresh 1
```

**Exit:**
- Press `Ctrl+C` to stop monitoring and return to shell

**Return Codes:**
- `0`: Success - monitoring stopped normally (Ctrl+C)
- `1`: Error - deployment not found
- `130`: Interrupted by user (Ctrl+C)

---

### history

Show restart history for a deployment.

**Synopsis:**
```bash
claude-mpm local-deploy history <deployment-id>
```

**Required Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `deployment-id` | string | Deployment ID to check |

**Output:**

```
Restart History: deployment-20251022-a3f7b2c1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Metric            ┃ Value  ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ Total Restarts    │ 5      │
│ Successful        │ 4      │
│ Failed            │ 1      │
│ Circuit Breaker   │ CLOSED │
└───────────────────┴────────┘

Recent Restart Attempts
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ #    ┃ Timestamp           ┃ Result    ┃ Reason                         ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 5    │ 2025-10-22 14:23:15 │ ✓ Success │ Health check failure           │
│ 4    │ 2025-10-22 12:45:30 │ ✓ Success │ Process crash (exit code 1)    │
│ 3    │ 2025-10-22 11:12:08 │ ✓ Success │ Memory leak detected           │
│ 2    │ 2025-10-22 09:34:22 │ ✗ Failed  │ Circuit breaker opened         │
│ 1    │ 2025-10-22 08:15:45 │ ✓ Success │ Process crash (exit code 137)  │
└──────┴─────────────────────┴───────────┴────────────────────────────────┘

Circuit Breaker Status: CLOSED
Last Reset: Never
Next Allowed Restart: Immediately
```

**Examples:**

```bash
# Show restart history
claude-mpm local-deploy history deployment-20251022-a3f7b2c1

# Check if circuit breaker is open
claude-mpm local-deploy history deployment-20251022-a3f7b2c1 | grep "Circuit Breaker"
```

**Return Codes:**
- `0`: Success - history retrieved
- `1`: Error - deployment not found

---

### enable-auto-restart

Enable automatic restart for a deployment.

**Synopsis:**
```bash
claude-mpm local-deploy enable-auto-restart <deployment-id>
```

**Required Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `deployment-id` | string | Deployment ID to enable auto-restart for |

**Behavior:**

1. Enables crash detection
2. Configures restart policy from config file or defaults
3. Starts monitoring for crashes
4. Applies exponential backoff and circuit breaker

**Output:**

```
Auto-restart enabled for deployment-20251022-a3f7b2c1

Configuration:
• Max attempts: 5
• Initial backoff: 2.0 seconds
• Max backoff: 300.0 seconds
• Circuit breaker threshold: 3 failures
• Circuit breaker window: 5 minutes
• Circuit breaker reset: 10 minutes

Status: Active
```

**Examples:**

```bash
# Enable auto-restart
claude-mpm local-deploy enable-auto-restart deployment-20251022-a3f7b2c1

# Verify it's enabled
claude-mpm local-deploy status deployment-20251022-a3f7b2c1 | grep "Auto-Restart"
```

**Return Codes:**
- `0`: Success - auto-restart enabled
- `1`: Error - deployment not found
- `2`: Error - already enabled

---

### disable-auto-restart

Disable automatic restart for a deployment.

**Synopsis:**
```bash
claude-mpm local-deploy disable-auto-restart <deployment-id>
```

**Required Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `deployment-id` | string | Deployment ID to disable auto-restart for |

**Behavior:**

1. Stops crash detection
2. Removes restart policy
3. Stops monitoring for crashes
4. Process will stay crashed if it fails

**Output:**

```
Auto-restart disabled for deployment-20251022-a3f7b2c1

Status: Inactive
Process will NOT restart on crash
```

**Examples:**

```bash
# Disable auto-restart
claude-mpm local-deploy disable-auto-restart deployment-20251022-a3f7b2c1

# Verify it's disabled
claude-mpm local-deploy status deployment-20251022-a3f7b2c1 | grep "Auto-Restart"
```

**Return Codes:**
- `0`: Success - auto-restart disabled
- `1`: Error - deployment not found
- `2`: Error - already disabled

---

## Configuration File Reference

**Location**: `.claude-mpm/local-ops-config.yaml`

**Example File**: `.claude-mpm/local-ops-config.yaml.example`

### Complete Schema

```yaml
version: "1.0"

# Default settings for all deployments
defaults:
  # Health check interval in seconds
  # Lower = faster detection, higher CPU usage
  # Higher = slower detection, lower CPU usage
  health_check_interval_seconds: 30

  # Enable auto-restart by default for new deployments
  auto_restart_enabled: false

# Restart policy configuration
restart_policy:
  # Maximum restart attempts before giving up
  max_attempts: 5

  # Initial delay between restarts (seconds)
  initial_backoff_seconds: 2.0

  # Maximum delay between restarts (seconds)
  max_backoff_seconds: 300.0

  # Exponential backoff multiplier
  # Delay calculation: initial * (multiplier ^ attempt)
  backoff_multiplier: 2.0

  # Circuit breaker: failures before opening circuit
  circuit_breaker_threshold: 3

  # Circuit breaker: time window for counting failures (seconds)
  circuit_breaker_window_seconds: 300

  # Circuit breaker: time before attempting to close circuit (seconds)
  circuit_breaker_reset_seconds: 600

# Stability monitoring configuration
stability:
  # Memory leak threshold (MB growth per minute)
  # Trigger preemptive restart if exceeded
  memory_leak_threshold_mb_per_minute: 10.0

  # File descriptor threshold (percent of system limit)
  # 0.8 = 80% of ulimit -n
  fd_threshold_percent: 0.8

  # Maximum thread count before triggering restart
  thread_threshold: 1000

  # Maximum network connection count
  connection_threshold: 500

  # Minimum free disk space (MB)
  disk_threshold_mb: 100

# Log monitoring configuration
log_monitoring:
  # Enable log file monitoring
  enabled: true

  # Error patterns to detect in logs (regex supported)
  error_patterns:
    - "OutOfMemoryError"
    - "Segmentation fault"
    - "Exception:"
    - "Error:"
    - "FATAL"
    - "CRITICAL"
    - "panic:"
    - "AssertionError"
    - "UnhandledPromiseRejectionWarning"
```

### Configuration Sections

#### defaults

Global settings applied to all deployments.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `health_check_interval_seconds` | integer | 30 | Interval between health checks |
| `auto_restart_enabled` | boolean | false | Default auto-restart setting |

#### restart_policy

Controls auto-restart behavior and circuit breaker.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_attempts` | integer | 5 | Maximum restart attempts |
| `initial_backoff_seconds` | float | 2.0 | Starting delay between restarts |
| `max_backoff_seconds` | float | 300.0 | Maximum delay cap |
| `backoff_multiplier` | float | 2.0 | Exponential multiplier |
| `circuit_breaker_threshold` | integer | 3 | Failures before opening |
| `circuit_breaker_window_seconds` | integer | 300 | Time window for failures |
| `circuit_breaker_reset_seconds` | integer | 600 | Reset timeout |

#### stability

Resource monitoring thresholds.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `memory_leak_threshold_mb_per_minute` | float | 10.0 | Memory growth rate trigger |
| `fd_threshold_percent` | float | 0.8 | File descriptor threshold |
| `thread_threshold` | integer | 1000 | Thread count limit |
| `connection_threshold` | integer | 500 | Network connection limit |
| `disk_threshold_mb` | integer | 100 | Minimum free disk space |

#### log_monitoring

Log file error detection.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | boolean | true | Enable log monitoring |
| `error_patterns` | array | (see above) | Error patterns to detect |

### Customization Examples

**More aggressive health checks**:
```yaml
defaults:
  health_check_interval_seconds: 10  # Check every 10s
```

**Higher memory leak threshold**:
```yaml
stability:
  memory_leak_threshold_mb_per_minute: 20.0  # Allow 20 MB/min growth
```

**Custom error patterns**:
```yaml
log_monitoring:
  enabled: true
  error_patterns:
    - "OutOfMemoryError"
    - "DatabaseConnectionError"
    - "APIError"
    - "Custom error: .*critical.*"
```

**Longer circuit breaker timeout**:
```yaml
restart_policy:
  circuit_breaker_reset_seconds: 1800  # 30 minutes
```

## Return Codes

All commands use consistent return codes:

| Code | Meaning | Example |
|------|---------|---------|
| `0` | Success | Command completed successfully |
| `1` | General error | Deployment not found, process error |
| `2` | Invalid arguments | Missing required argument, invalid value |
| `3` | Configuration error | Invalid config file, missing settings |
| `130` | User interrupt | User pressed Ctrl+C |

### Checking Return Codes

```bash
# Check if command succeeded
if claude-mpm local-deploy start --command "npm run dev" --port 3000; then
  echo "Started successfully"
else
  echo "Start failed with code $?"
fi

# Store deployment ID only if successful
DEPLOYMENT_ID=$(claude-mpm local-deploy start --command "npm run dev" --port 3000)
if [ $? -eq 0 ]; then
  echo "Deployment ID: $DEPLOYMENT_ID"
fi

# Different handling for different errors
claude-mpm local-deploy stop deployment-abc123
case $? in
  0) echo "Stopped successfully" ;;
  1) echo "Deployment not found" ;;
  2) echo "Failed to stop process" ;;
  130) echo "Interrupted by user" ;;
esac
```

## Examples

### Complete Deployment Workflow

```bash
# 1. Start deployment with full monitoring
DEPLOYMENT_ID=$(claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --auto-restart \
  --log-file ./logs/nextjs.log \
  --env NODE_ENV=development)

echo "Started: $DEPLOYMENT_ID"

# 2. Check initial health
claude-mpm local-deploy health $DEPLOYMENT_ID

# 3. Monitor for 30 seconds
timeout 30 claude-mpm local-deploy monitor $DEPLOYMENT_ID || true

# 4. Check comprehensive status
claude-mpm local-deploy status $DEPLOYMENT_ID

# 5. Verify running
claude-mpm local-deploy list --status running | grep $DEPLOYMENT_ID

# 6. Stop when done
claude-mpm local-deploy stop $DEPLOYMENT_ID
```

### Multi-Service Deployment

```bash
# Start multiple services
API_ID=$(claude-mpm local-deploy start \
  --command "npm run start:api" \
  --port 8080 \
  --auto-restart)

WEB_ID=$(claude-mpm local-deploy start \
  --command "npm run dev" \
  --port 3000 \
  --auto-restart)

WORKER_ID=$(claude-mpm local-deploy start \
  --command "python worker.py" \
  --auto-restart \
  --log-file ./logs/worker.log)

# List all deployments
claude-mpm local-deploy list

# Stop all services
for ID in $API_ID $WEB_ID $WORKER_ID; do
  claude-mpm local-deploy stop $ID
done
```

### Health Monitoring Script

```bash
#!/bin/bash
# health-monitor.sh - Monitor deployment health

DEPLOYMENT_ID=$1

while true; do
  HEALTH=$(claude-mpm local-deploy health $DEPLOYMENT_ID 2>/dev/null | grep "Overall" | awk '{print $3}')

  case $HEALTH in
    "HEALTHY")
      echo "$(date): ✓ Healthy"
      ;;
    "DEGRADED")
      echo "$(date): ⚠ Degraded - investigating..."
      claude-mpm local-deploy status $DEPLOYMENT_ID
      ;;
    "UNHEALTHY")
      echo "$(date): ✗ Unhealthy - alerting..."
      # Send alert (e.g., Slack, email)
      ;;
    *)
      echo "$(date): ? Unknown status"
      ;;
  esac

  sleep 60
done
```

### Automated Deployment Script

```bash
#!/bin/bash
# deploy.sh - Automated deployment with verification

set -e

COMMAND=$1
PORT=$2

echo "Starting deployment..."
DEPLOYMENT_ID=$(claude-mpm local-deploy start \
  --command "$COMMAND" \
  --port $PORT \
  --auto-restart \
  --log-file ./logs/deployment.log)

echo "Deployment ID: $DEPLOYMENT_ID"

# Wait for startup
sleep 5

# Verify health
echo "Checking health..."
HEALTH=$(claude-mpm local-deploy health $DEPLOYMENT_ID | grep "Overall" | awk '{print $3}')

if [ "$HEALTH" != "HEALTHY" ]; then
  echo "ERROR: Deployment unhealthy"
  claude-mpm local-deploy stop $DEPLOYMENT_ID
  exit 1
fi

echo "✓ Deployment healthy"
echo "✓ URL: http://localhost:$PORT"
echo "✓ Monitor: claude-mpm local-deploy monitor $DEPLOYMENT_ID"
```

## PM2 Monitoring Enhancements (v2.0.0+)

The `local-deploy` CLI has been enhanced with advanced PM2 monitoring capabilities specifically optimized for Next.js deployments. These features are automatically enabled when deploying Node.js applications.

### PM2 Memory Restart Configuration

When deploying Next.js applications, the CLI automatically configures PM2 with production-ready memory management:

**Configuration Applied**:
- **Memory Limit**: 2G with automatic restart
- **Max Restarts**: 10 with 3s minimum uptime
- **Graceful Shutdown**: 5s kill timeout, 8s listen timeout

**Example Deployment**:
```bash
# Next.js production with PM2 monitoring
claude-mpm local-deploy start \
  --command "npm start" \
  --port 3000 \
  --auto-restart

# The CLI automatically executes:
# pm2 start npm --name 'app' -- start \
#   --max-memory-restart 2G \
#   --max-restarts 10 \
#   --min-uptime 3000
```

### Next.js Health Validation

The CLI performs 3-step validation for Next.js deployments:

1. **Endpoint Validation**: Tests `/api/health` and `/` endpoints
2. **Build Artifact Verification**: Checks `.next/BUILD_ID` and `.next/routes-manifest.json`
3. **Static Asset Checking**: Validates `/_next/static/chunks` directory

**Health Check Output**:
```bash
$ claude-mpm local-deploy health deployment-20251027-a3f7b2

Health Status: deployment-20251027-a3f7b2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall Health: HEALTHY

Individual Checks
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check Type      ┃ Status    ┃ Details                       ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ HTTP Endpoint   │ ✓ HEALTHY │ /api/health 200 OK (143ms)    │
│ Build Artifacts │ ✓ HEALTHY │ BUILD_ID and routes present   │
│ Static Assets   │ ✓ HEALTHY │ 47 chunks found               │
└─────────────────┴───────────┴───────────────────────────────┘
```

### PM2 Metrics Extraction

The CLI extracts real-time metrics from PM2 for monitoring and alerting:

**Tracked Metrics**:
- `restart_count`: Number of restarts since deployment
- `uptime`: Process uptime in milliseconds
- `memory_usage`: Current memory usage in MB
- `cpu_percent`: Current CPU utilization percentage
- `status`: Process status (online, stopped, errored)

**Status Command Output**:
```bash
$ claude-mpm local-deploy status deployment-20251027-a3f7b2

Deployment Status: deployment-20251027-a3f7b2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PM2 Process Information
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field            ┃ Value                    ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ PM2 ID           │ 0                        │
│ Status           │ online                   │
│ Restarts         │ 2                        │
│ Uptime           │ 2h 34m 12s               │
│ Memory           │ 456 MB / 2048 MB (22%)   │
│ CPU              │ 2.3%                     │
└──────────────────┴──────────────────────────┘
```

### Smart Alerts

The CLI provides intelligent alerting based on PM2 metrics:

**Restart Alert** (threshold: 5 restarts):
```
⚠️  High restart count detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Deployment: deployment-20251027-a3f7b2
Restarts:   7 (threshold: 5)
Action:     Investigate logs and recent errors

$ pm2 logs deployment-20251027-a3f7b2 --lines 50
```

**Memory Alert** (threshold: 1.8G / 90% of limit):
```
⚠️  Memory usage approaching limit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Deployment: deployment-20251027-a3f7b2
Memory:     1843 MB / 2048 MB (90%)
Action:     Preemptive investigation recommended

Trend:      +15 MB/min (memory leak possible)
```

### PM2 Command Integration

The CLI integrates with PM2 commands for advanced monitoring:

```bash
# View PM2 process list in JSON format
pm2 jlist

# Get detailed process information
pm2 describe deployment-20251027-a3f7b2

# Show real-time metrics
pm2 show deployment-20251027-a3f7b2

# Monitor all processes
pm2 monit
```

### Configuration

PM2 monitoring can be customized in `.claude-mpm/local-ops-config.yaml`:

```yaml
pm2_monitoring:
  metrics_extraction:
    enabled: true
    commands:
      status: "pm2 jlist"
      describe: "pm2 describe {app_name}"
      metrics: "pm2 show {app_name}"

  alerts:
    restart_threshold: 5
    memory_threshold_percent: 90
    cpu_threshold_percent: 80

deployment_strategies:
  production:
    nextjs:
      pm2_options:
        max_memory_restart: "2G"
        max_restarts: 10
        min_uptime: 3000
        autorestart: true
        kill_timeout: 5000
        listen_timeout: 8000
```

### Troubleshooting PM2 Deployments

**High Restart Count**:
```bash
# Check restart reasons
pm2 describe <app_name> | grep "restart\|error"

# View error logs
pm2 logs <app_name> --err --lines 100

# Increase restart threshold if needed
# Edit .claude-mpm/local-ops-config.yaml
pm2_monitoring:
  alerts:
    restart_threshold: 10
```

**Memory Issues**:
```bash
# Monitor memory in real-time
pm2 monit

# Check memory trend
claude-mpm local-deploy status <deployment-id> | grep "Memory"

# Increase memory limit
# Edit .claude-mpm/local-ops-config.yaml
deployment_strategies:
  production:
    nextjs:
      pm2_options:
        max_memory_restart: "3G"
```

### Benefits

- **Automatic Configuration**: PM2 monitoring enabled automatically for Next.js
- **Production Ready**: Memory restart and circuit breaker prevent crashes
- **Real-time Visibility**: Live metrics and smart alerts
- **Proactive Detection**: Alerts before critical thresholds are reached
- **Easy Integration**: Works seamlessly with existing `local-deploy` commands

For more details, see:
- **[Local Ops Agent Documentation](../agents/LOCAL_OPS_AGENT.md)** - Complete PM2 monitoring guide
- **[Next.js PM2 Monitoring](../agents/LOCAL_OPS_AGENT.md#nextjs-pm2-monitoring-enhancements-v200)** - Detailed feature documentation

---

## Related Documentation

- **[Local Ops Agent](../agents/LOCAL_OPS_AGENT.md)** - Complete agent documentation with PM2 monitoring
- **[User Guide](../user/03-features/local-process-management.md)** - End-user documentation
- **[Developer Guide](../developer/LOCAL_PROCESS_MANAGEMENT.md)** - Architecture and implementation
- **[General CLI Reference](CLI_COMMANDS.md)** - Other Claude MPM commands
- **[Configuration Guide](CONFIGURATION.md)** - General configuration reference

---

This comprehensive CLI reference provides complete documentation for all `local-deploy` commands with examples, options, and configuration details for effective local process management, including enhanced PM2 monitoring for production-ready deployments.
