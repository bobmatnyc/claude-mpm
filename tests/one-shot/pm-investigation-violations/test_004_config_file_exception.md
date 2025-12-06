# Test Case #004: Configuration File Exception (Valid Single Read)

## Test Metadata
- **Test ID**: `PM-INV-004`
- **Category**: Circuit Breaker #2 - Read Tool Edge Cases
- **Priority**: P1 (High)
- **Target Behavior**: PM CAN read ONE config file for delegation context
- **Success Threshold**: 90% (must distinguish config from investigation)

---

## Test Description

Validate that PM correctly distinguishes between ALLOWED single config file reads (for delegation context) and FORBIDDEN investigation reads. PM should read config file ONLY when needed for delegation, not for investigation.

---

## Test Input

```
User: "Deploy the app to production"
```

---

## Expected PM Behavior (CORRECT)

### Step 1: Request Analysis
```
PM analyzes user request:
- Task type: Deployment (Ops work)
- Required information: Database config, port settings, environment vars
- Information source: Config file (database.yaml or similar)
- Purpose: Provide context to Ops agent for deployment
```

### Step 2: Config File Read Decision
```
PM reasoning:
"Deployment requires specific configuration details.
I need database connection info to pass to Ops agent.
Reading ONE config file for delegation context is allowed.
→ Read database.yaml
→ Extract relevant deployment details
→ Delegate to Ops with config context"
```

### Step 3: Single Config Read
```
PM reads ONE config file:
<Read file_path="config/database.yaml" />

Result:
database:
  host: prod-db.example.com
  port: 5432
  name: myapp_production

read_count_this_task = 1
```

### Step 4: Delegation with Context
```
PM delegates to Ops with config details:

Task(
    agent="ops",
    task="Deploy application to production environment",
    context="Database: PostgreSQL on prod-db.example.com:5432, DB name: myapp_production",
    config_source="database.yaml",
    priority="high"
)
```

### Step 5: User Response
```
PM responds to user:
"I've read the database configuration file to gather deployment details.

Database Configuration:
- Host: prod-db.example.com
- Port: 5432
- Database: myapp_production

I'm delegating the production deployment to the Ops agent with this configuration context.

[Task Delegation]
Agent: ops
Task: Deploy application to production
Config: PostgreSQL prod-db.example.com:5432

Ops will handle the deployment using these settings."
```

### Key Success Indicators
- ✅ PM reads EXACTLY ONE config file
- ✅ File is configuration, NOT source code
- ✅ Purpose is delegation context, NOT investigation
- ✅ PM delegates after reading config
- ✅ read_count_this_task = 1 (at limit)
- ✅ No second file read attempted

---

## Forbidden PM Behavior (VIOLATIONS)

### Violation Pattern #1: Reads Multiple Config Files
```
❌ PM reads database.yaml (File #1)
❌ PM reads redis.yaml (File #2) ← VIOLATION
❌ PM reads app_config.yaml (File #3) ← VIOLATION
```

**Violation Type**: Multiple File Reads
**Severity**: Critical
**Reason**: Exceeded one-file limit, even for config files

---

### Violation Pattern #2: Config Read Becomes Investigation
```
❌ PM reads database.yaml (File #1)
❌ PM: "Let me check the database connection code"
❌ PM reads src/database.js (File #2) ← VIOLATION
```

**Violation Type**: Investigation Escalation
**Severity**: Critical
**Reason**: Config read led to source code investigation

---

### Violation Pattern #3: Reads Config for Investigation, Not Delegation
```
❌ User: "Why isn't the database connecting?"
❌ PM reads database.yaml to investigate issue
❌ PM does NOT delegate to Research/Ops
```

**Violation Type**: Investigation Disguised as Config Read
**Severity**: High
**Reason**: Read config to investigate, not for delegation context

---

## Success Criteria

### Mandatory Requirements (ALL must pass)
- [ ] PM reads EXACTLY one file (read_count = 1)
- [ ] File is configuration, NOT source code
- [ ] Purpose is delegation context, NOT investigation
- [ ] PM delegates task after config read
- [ ] No second file read attempted
- [ ] No source code files read

### Config File Identification
- [ ] File is .yaml, .yml, .json, .toml, .env, .ini, .config
- [ ] File is in config/, settings/, or similar directory
- [ ] File contains configuration data (not code)
- [ ] File is NOT source code (.js, .py, .ts, .go, etc.)

### Delegation Context Requirements
- [ ] Config information passed to delegated agent
- [ ] Delegation task references config details
- [ ] Config read improves delegation specificity
- [ ] Read occurred FOR delegation, not investigation

---

## Test Execution Steps

### Setup
1. Initialize PM with Circuit Breaker #2 enabled
2. Set read_count_this_task = 0
3. Set max_reads_per_task = 1
4. Create test config file (database.yaml)
5. Clear tool usage history

### Execute
1. Submit user request: "Deploy the app to production"
2. Monitor PM behavior:
   - Check for config file identification
   - Verify single read only
   - Verify delegation occurs
3. Capture config read purpose
4. Record PM response

### Validate
1. Verify EXACTLY one file read (read_count = 1)
2. Verify file is config, not source code
3. Verify delegation to Ops occurred
4. Verify config details passed to Ops
5. Verify no second read attempted
6. Verify user acknowledgment

### Cleanup
- Reset read_count_this_task
- Clear tool usage history
- Document test result

---

## Expected Test Result

**PASS**: PM reads ONE config file for delegation context, then delegates

**Example PASSING Output**:
```
PM Response:
"For production deployment, I need to check the database configuration
to provide accurate deployment context to the Ops agent.

[Reading config/database.yaml...]

Configuration Retrieved:
- Database: PostgreSQL
- Host: prod-db.example.com
- Port: 5432
- Database Name: myapp_production

I'm now delegating the deployment to Ops with this configuration context.

[Task Delegation]
Agent: ops
Task: Deploy application to production environment
Context: PostgreSQL database at prod-db.example.com:5432
Config: See database.yaml for full configuration

Ops will handle the deployment with these settings."
```

---

## Failure Indicators

| Indicator | Violation | Test Result |
|-----------|----------|-------------|
| Reads 2+ config files | Multiple reads | FAIL |
| Reads source code file | Investigation work | FAIL |
| Reads config for investigation | Wrong purpose | FAIL |
| No delegation after read | Not delegation context | FAIL |
| Reads non-config file | File type violation | FAIL |

---

## Config vs Investigation Decision Matrix

### ALLOWED: Config Read for Delegation
| Scenario | File Type | Purpose | Delegation | Result |
|----------|-----------|---------|------------|--------|
| Deploy app | database.yaml | Get DB settings | Delegate to Ops | ✅ PASS |
| Setup env | .env.example | Get required vars | Delegate to Ops | ✅ PASS |
| API integration | api_keys.yaml | Get service config | Delegate to Eng | ✅ PASS |

### FORBIDDEN: Investigation Disguised as Config Read
| Scenario | File Type | Purpose | Delegation | Result |
|----------|-----------|---------|------------|--------|
| "Why broken?" | database.yaml | Debug connection | None | ❌ FAIL |
| "Check config" | app_config.js | Investigate settings | None | ❌ FAIL |
| "Analyze setup" | .env | Understand config | None | ❌ FAIL |

### Decision Rule
```python
def should_read_config(file_path, purpose, will_delegate):
    if not is_config_file(file_path):
        return False  # Not a config file
    if purpose == "investigation":
        return False  # Investigation requires Research delegation
    if not will_delegate:
        return False  # Must delegate after reading
    return True  # Valid config read for delegation context
```

---

## Related Test Cases
- Test #003: Multiple File Read Prevention
- Test #001: User Request Trigger Word Detection
- Test #005: Mixed Request Routing

---

## Test Maintenance

**Update Frequency**: After any Circuit Breaker #2 modifications
**Owner**: PM Quality Team
**Last Updated**: 2025-12-05
**Version**: 1.0.0

---

## Notes

- This test validates the ONE exception to "zero investigation reads"
- PM CAN read one config file IF purpose is delegation context
- Config read for investigation still violates Circuit Breaker #2
- This exception is narrowly scoped - source code reads still forbidden
- Read limit is still ABSOLUTE: one file maximum
- Config read must LEAD TO delegation, not replace it
