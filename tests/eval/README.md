# PM Eval Test Suite

Automated evaluation system for testing PM agent instruction compliance.  
The mock-based suite tests structural correctness; the live suite calls the real
Anthropic API to verify actual behavioral routing.

---

## Directory overview

```
tests/eval/
├── conftest.py                 # Shared fixtures (PMResponseCapture, ResponseReplay, etc.)
├── README.md                   # This file
├── test_quickstart_demo.py     # Quick smoke-test demo (no API key needed)
├── metrics/                    # Custom DeepEval metric classes
├── scenarios/                  # JSON scenario definitions
│   └── pm_behavioral_requirements.json   # 76 scenarios
├── test_cases/
│   ├── test_pm_behavioral_compliance.py  # Mock-based compliance tests
│   ├── test_pm_live_evals.py             # Live API eval runner  ← NEW
│   └── ...
├── golden_responses/           # Cached API responses (gitignored binary)
└── utils/
    └── pm_response_simulator.py  # Mock PM responses
```

---

## Running evals

### Fast (mock-based, always passes without API key)

```bash
uv run pytest tests/eval/ -m "not live_eval and not tmux_eval" -v
```

### Live (real Anthropic API calls)

```bash
# Requires ANTHROPIC_API_KEY and PM_EVAL_LIVE=1
PM_EVAL_LIVE=1 uv run pytest tests/eval/ -m live_eval -v
```

### Tmux-based (most realistic, tests running PM instance)

```bash
# 1. Start the test PM instance in a tmux session
tmux kill-session -t mpm-eval 2>/dev/null || true
tmux new-session -d -s mpm-eval -c /Volumes/Kemono/Users/masa/Projects/claude-mpm
tmux send-keys -t mpm-eval "claude --model claude-haiku-4-5" Enter

# 2. Run tmux evals (requires PM_EVAL_TMUX=1)
PM_EVAL_TMUX=1 uv run pytest tests/eval/ -m tmux_eval -v

# 3. Check instance status
tmux capture-pane -t mpm-eval -p

# 4. Clean up when done
tmux kill-session -t mpm-eval
```

### Regenerate golden responses (force re-run against API)

```bash
PM_EVAL_LIVE=1 uv run pytest tests/eval/ -m live_eval --update-golden -v
```

### Collect without running (no API key needed)

```bash
uv run pytest tests/eval/test_cases/test_pm_live_evals.py -m live_eval --collect-only -v
```

---

## Live eval details

**File:** `tests/eval/test_cases/test_pm_live_evals.py`

### Selected scenarios (13 critical)

| Scenario | Category | What it tests |
|---|---|---|
| DEL-001 | delegation | PM delegates implementation to engineer (never Edit/Write) |
| DEL-002 | delegation | PM delegates investigation to Research (never Grep/multiple Read) |
| DEL-003 | delegation | PM delegates testing to QA agent |
| DEL-005 | delegation / ticket | PM delegates ticket ops to Ticketing (not WebFetch/mcp-ticketer) |
| DEL-010 | delegation | PM executes full workflow automatically, no unnecessary permission requests |
| CB1-001 | circuit_breaker | CB#1: no direct code implementation (Edit/Write forbidden) |
| CB2-001 | circuit_breaker | CB#2: no direct code investigation (Grep/Glob forbidden) |
| CB3-001 | circuit_breaker | CB#3: no completion claims without agent evidence |
| CB3-002 | circuit_breaker | CB#3: no forbidden phrases ("looks good", "should work", etc.) |
| CB6-001 | circuit_breaker | CB#6: no direct ticket access via WebFetch or mcp-ticketer |
| CB7-001 | circuit_breaker | CB#7: Research Gate invoked for ambiguous tasks |
| EV-001  | evidence | Implementation claims require files changed + commit hash |
| WF-003  | workflow | QA is mandatory after every implementation |

### Model

Default: `claude-haiku-4-5` (cheapest, sufficient for routing checks).  
Override: `PM_EVAL_MODEL=<model-id> PM_EVAL_LIVE=1 uv run pytest ...`

### Caching

Golden responses are cached in `tests/eval/golden_responses/` using the naming
convention:

```
{scenario_id}_{model}_{prompt_hash_8chars}.json
```

- First run with `PM_EVAL_LIVE=1`: calls API, saves cache.
- Subsequent runs without `PM_EVAL_LIVE=1`: loads from cache.
- `--update-golden`: forces API re-call even if cache exists.

### Cost guard

Without `PM_EVAL_LIVE=1` the suite either loads cached responses or skips with:

```
No cached response for <id>. Run with PM_EVAL_LIVE=1 to generate golden responses.
```

---

## Mock-based suite

The existing test files under `test_cases/` use simulated responses from
`utils/pm_response_simulator.py`.  They always pass without an API key and are
the primary fast-feedback path in CI.

---

## References

- PM Instructions: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
- Circuit Breakers: `src/claude_mpm/agents/templates/circuit-breakers.md`
- Scenarios: `tests/eval/scenarios/pm_behavioral_requirements.json`
