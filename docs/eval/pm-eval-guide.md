# PM Behavioral Evaluation Guide

## Overview

The PM (Project Manager agent) is evaluated through three complementary layers:

1. **Structural Invariants** — Fast unit tests that verify prompt assembly (always run in CI)
2. **Lazy-Load Effectiveness** — Tests verifying that context optimization works (always run in CI)
3. **Live API Evals** — Behavioral evaluation against real Claude API (opt-in, requires ANTHROPIC_API_KEY)
4. **Tmux Instance Evals** — Interactive testing against a live mpm session (opt-in, requires tmux setup)

This layered approach ensures PM behavior is correct at multiple granularities, from system prompt structure to real-world behavioral compliance.

## Evaluation Layers

| Layer | Test File | Runs in CI | Calls LLM | Speed |
|---|---|---|---|---|
| **Structural invariants** | `tests/test_assembled_prompt_snapshot.py` | Always | No | <1s |
| **Lazy-load effectiveness** | `tests/test_lazy_load_workflow.py` | Always | No | <1s |
| **Live API evals** | `tests/eval/test_cases/test_pm_live_evals.py` | Opt-in | Yes | ~30-60s per scenario |
| **Tmux instance evals** | `tests/eval/test_cases/test_pm_tmux_evals.py` | Opt-in | Yes (via tmux) | ~15-30s per scenario |

## Layer 1: Structural Invariants

**File**: `tests/test_assembled_prompt_snapshot.py`

Fast unit tests that verify the assembled system prompt meets basic invariants:

- `<example>` blocks are stripped from capability descriptions
- PM_memories.md injection is conditional (skipped for MCP backends)
- Required sections are present (AGENTS, PM_WORKFLOW_REFERENCE, MEMORY)
- System prompt size is within bounds (~11,500-12,000 tokens)
- Snapshot matches golden baseline (detects unexpected changes)

```bash
uv run pytest tests/test_assembled_prompt_snapshot.py -v
```

**Why it matters**: Catches prompt assembly bugs before they reach the LLM.

## Layer 2: Lazy-Load Effectiveness

**File**: `tests/test_lazy_load_workflow.py`

Verifies that context optimization (lazy-loading WORKFLOW.md) works correctly:

- Base system prompt does not include system-level WORKFLOW.md
- Project-level WORKFLOW.md overrides are still embedded verbatim
- User-level WORKFLOW.md overrides are still embedded verbatim
- External reference to `docs/workflow/PM_WORKFLOW.md` is present

```bash
uv run pytest tests/test_lazy_load_workflow.py -v
```

**Why it matters**: Ensures we saved context without losing functionality for projects with custom workflows.

## Layer 3: Live API Evals

**File**: `tests/eval/test_cases/test_pm_live_evals.py`

Behavioral evaluation using the real Anthropic API. Tests run against predefined scenarios with expected outputs.

### Running Live Evals

```bash
# Requires ANTHROPIC_API_KEY to be set
PM_EVAL_LIVE=1 uv run pytest tests/eval/test_cases/test_pm_live_evals.py -m live_eval -v
```

### Updating Golden Responses

When PM behavior intentionally changes (e.g., new delegation strategy), regenerate golden responses:

```bash
PM_EVAL_LIVE=1 uv run pytest tests/eval/test_cases/test_pm_live_evals.py -m live_eval --update-golden -v
```

This stores the new PM responses as the expected baseline for future runs.

### Anatomy of a Scenario

Scenarios are defined in the test file with:

- **id**: Unique scenario identifier (e.g., `pm_handles_ambiguous_requirements`)
- **prompt**: User prompt to send to PM
- **expected_patterns**: List of regex patterns the response must match
- **forbidden_patterns**: List of regex patterns the response must NOT contain

Example:

```python
{
    "id": "pm_handles_ambiguous_requirements",
    "prompt": "Build a system that is fast and reliable. I'm not sure what tech stack to use.",
    "expected_patterns": [
        r"clarify.*requirement",
        r"(?:architecture|design).*decision",
    ],
    "forbidden_patterns": [
        r"i don't know",  # PM should be confident
        r"(?:not|no).*my.*job",  # PM should engage
    ],
}
```

### Adding New Scenarios

1. Open `tests/eval/test_cases/test_pm_live_evals.py`
2. Add a new dict to the `SCENARIOS` list
3. Run with `--update-golden` to capture the first response
4. Review captured response carefully
5. Adjust `expected_patterns` and `forbidden_patterns` based on what you saw
6. Run again without `--update-golden` to verify patterns match

### Why Live Evals Matter

Live evals test PM behavior against the real LLM, catching:
- Hallucinations or contradictions in PM responses
- Deviations from documented PM responsibilities
- Regressions in delegation logic or error handling
- Tone/style inconsistencies

## Layer 4: Tmux Instance Evals

**File**: `tests/eval/test_cases/test_pm_tmux_evals.py`

Interactive testing against a live mpm session running in tmux. This tests PM behavior in a real CLI environment with all hooks and services active.

### Prerequisites

Tmux must be installed:

```bash
# macOS
brew install tmux

# Ubuntu/Debian
sudo apt-get install tmux

# Verify installation
tmux -V
```

### Running Tmux Evals

```bash
# Step 1: Create and start a fresh mpm eval session
# (This kills any existing session and starts a new one)
tmux kill-session -t mpm-eval 2>/dev/null || true
tmux new-session -d -s mpm-eval -c /Volumes/Kemono/Users/masa/Projects/claude-mpm
tmux send-keys -t mpm-eval 'claude --model claude-haiku-4-5' Enter

# Give the session time to start
sleep 5

# Step 2: Run the tests
PM_EVAL_TMUX=1 uv run pytest tests/eval/test_cases/test_pm_tmux_evals.py -m tmux_eval -v

# Step 3 (optional): View the session afterward for debugging
tmux capture-pane -t mpm-eval -p
```

### Anatomy of a Tmux Scenario

Scenarios use the same structure as live API evals:

```python
{
    "id": "pm_responds_to_help_request",
    "prompt": "help",
    "expected_patterns": [
        r"help.*available|available.*help",
        r"(?:command|agent)",
    ],
    "forbidden_patterns": [
        r"error",
        r"unknown.*command",
    ],
}
```

### TmuxPMClient Architecture

**File**: `tests/eval/utils/tmux_pm_client.py`

The `TmuxPMClient` class handles interaction with the tmux session:

#### Sending Prompts

```python
client = TmuxPMClient(session_name="mpm-eval")
response = client.send_prompt("delegate to engineer: build a todo app")
```

The client:
1. Sends the prompt via `tmux send-keys`
2. Waits for output to appear
3. Polls `capture-pane` every 500ms
4. Waits until output is stable (no new lines for 2 seconds)
5. Strips ANSI escape codes from the response
6. Returns the clean text

#### Resetting Between Tests

```python
client.reset()  # Sends Ctrl+C to interrupt any running command
```

This clears the session state between test scenarios.

#### Error Handling

If output doesn't stabilize within a timeout (default 30s), the client raises `TmuxTimeoutError`. This helps catch hanging sessions or tests that expect output that never arrives.

### Why Tmux Evals Matter

Tmux evals test PM behavior with:
- All hooks active (PreToolUse, PostToolUse, UserPromptSubmit, etc.)
- All services running (memory, sessions, etc.)
- Real terminal I/O and formatting
- Realistic user interaction patterns
- Integration with actual agent subprocesses

## The Mock Gap

The existing mock-based test suite (`tests/eval/test_cases/test_pm_behavioral_compliance.py`) contains 456 tests using a `MockPMAgent` with keyword-based routing.

**Important limitation**: These tests do NOT validate actual PM behavior. The mock agent self-validates against its own keyword rules, which doesn't catch:
- Real PM hallucinations or contradictions
- Actual behavior deviations from documented procedures
- Real prompt assembly issues
- LLM-specific edge cases

The structural + live API + tmux layers are the real behavioral gates that ensure PM correctness.

## Available Scenarios

All behavioral scenarios are defined in:

**File**: `tests/eval/scenarios/pm_behavioral_requirements.json`

This file contains 76 predefined scenarios covering:

- Ambiguous requirements handling
- Error recovery
- Agent delegation
- Memory management
- Configuration validation
- Tool error handling
- Multi-turn conversations
- And more...

Currently, only 13 of these 76 scenarios are wired to live/tmux evals. To add more:

1. Open `test_pm_live_evals.py` or `test_pm_tmux_evals.py`
2. Load scenarios from `pm_behavioral_requirements.json`
3. Filter to desired subset (or add all)
4. Run with `--update-golden` to generate baselines

## Running All Eval Layers

### CI Pipeline (Fast, Always)

```bash
# Structural invariants + lazy-load tests
uv run pytest tests/test_assembled_prompt_snapshot.py tests/test_lazy_load_workflow.py -v
```

### Full Local Verification (Slow, Requires API Keys)

First, ensure your Anthropic API key is available in your shell:

```bash
# Run all layers
uv run pytest tests/test_assembled_prompt_snapshot.py tests/test_lazy_load_workflow.py -v
PM_EVAL_LIVE=1 uv run pytest tests/eval/test_cases/test_pm_live_evals.py -m live_eval -v

# 3. Optional: tmux evals
tmux kill-session -t mpm-eval 2>/dev/null || true
tmux new-session -d -s mpm-eval -c /Volumes/Kemono/Users/masa/Projects/claude-mpm
tmux send-keys -t mpm-eval 'claude --model claude-haiku-4-5' Enter
sleep 5
PM_EVAL_TMUX=1 uv run pytest tests/eval/test_cases/test_pm_tmux_evals.py -m tmux_eval -v
```

## Debugging Failed Evals

### Failed Structural Invariant

```bash
# Examine what changed
git diff tests/fixtures/assembled_prompt_golden.txt

# Review the actual assembled prompt
uv run pytest tests/test_assembled_prompt_snapshot.py -vvv

# If change is intentional, update golden:
PM_UPDATE_GOLDEN=1 uv run pytest tests/test_assembled_prompt_snapshot.py
```

### Failed Live Eval

```bash
# Re-run with verbose output
PM_EVAL_LIVE=1 uv run pytest tests/eval/test_cases/test_pm_live_evals.py::test_pm_live_evals[scenario_id] -vvv

# Check actual API response vs expected patterns
# (Look for patterns mismatch in pytest output)

# If intentional change, update golden:
PM_EVAL_LIVE=1 uv run pytest tests/eval/test_cases/test_pm_live_evals.py -m live_eval --update-golden -v
```

### Failed Tmux Eval

```bash
# Check session is still running
tmux list-sessions | grep mpm-eval

# View last output from session
tmux capture-pane -t mpm-eval -p

# Re-run specific test
PM_EVAL_TMUX=1 uv run pytest tests/eval/test_cases/test_pm_tmux_evals.py::test_pm_tmux_evals[scenario_id] -vvv

# Kill and restart if stuck
tmux kill-session -t mpm-eval
# Then re-run setup steps above
```

## Continuous Evaluation

For continuous monitoring of PM behavior:

```bash
# Watch structural tests (fast feedback)
watch -n 5 'uv run pytest tests/test_assembled_prompt_snapshot.py tests/test_lazy_load_workflow.py -q'

# Or with entr (re-run on file changes)
git ls-files tests/ | entr uv run pytest tests/test_assembled_prompt_snapshot.py tests/test_lazy_load_workflow.py
```

## Related Documentation

- [PM Context Optimization](./pm-context-optimization.md) — covers the optimizations being tested
- [Testing Guide](../guides/testing.md) — general testing patterns for claude-mpm
- [Agent Development](../guides/agent-development.md) — for creating new test agents
