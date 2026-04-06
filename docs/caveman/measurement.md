# Measurement Guide

How to validate that prompt changes do not degrade quality.

## Tooling

### analyze-mpm.py

The primary measurement tool lives in the `ai-coding-agent-token-usage` repo:
```
~/Projects/ai-coding-agent-token-usage/analysis/analyze.py
```

It extracts metrics from Claude Code session logs stored at:
```
~/.claude/projects/{project-path-slug}/{session-id}.jsonl
```

### Session Log Format

Each assistant message in the JSONL contains usage data:
```json
{
  "type": "assistant",
  "message": {
    "model": "claude-sonnet-4-20250514",
    "usage": {
      "input_tokens": 3,
      "cache_creation_input_tokens": 49347,
      "cache_read_input_tokens": 0,
      "output_tokens": 39
    }
  }
}
```

## A/B Test Methodology

### Prerequisites

1. A well-defined task (same task for both runs)
2. The verbose prompt on one branch (e.g., `main`)
3. The caveman prompt on another branch (e.g., `feat/caveman-prompt`)
4. The `analyze-mpm.py` tool configured

### Steps

1. **Baseline run**: On `main` branch, execute the test task. Save session ID.
2. **Caveman run**: On feature branch, execute the same task. Save session ID.
3. **Extract metrics**: Run `analyze.py` on both session logs.
4. **Compare**: Token counts, cost, cache hit rate.
5. **Quality assessment**: Manual review of both outputs using rubric.

### Same-Task Requirement

Use a standardized challenge for comparison. The pilot study used "Weather
Alerting Service" (Level 3 complexity) which requires:
- REST API with CRUD endpoints
- SQLite database with schema
- Background scheduler
- Mock/demo mode
- Dockerfile + docker-compose
- Tests
- README

This provides enough complexity to expose quality issues while being
reproducible across runs.

## Key Metrics

### Token Metrics (from session logs)

| Metric | Formula | Target |
|--------|---------|--------|
| Total input tokens | sum(input_tokens) | Lower is better |
| Total output tokens | sum(output_tokens) | Roughly constant |
| Cache creation | sum(cache_creation_input_tokens) | First turn only |
| Cache reads | sum(cache_read_input_tokens) | Higher is better |
| Cache hit rate | cache_read / (input + cache_read) | >80% |
| Turn count | count(assistant messages) | Lower is better |

### Cost Metrics

| Metric | Formula | Baseline |
|--------|---------|----------|
| Input cost | input_tokens * $3.00/M | Varies |
| Cached cost | cache_read * $0.30/M | 90% savings |
| Output cost | output_tokens * $15.00/M | Varies |
| Total cost | sum(all) | $6.74 verbose, $4.42 caveman |

### Derived Ratios

| Ratio | Formula | What It Shows |
|-------|---------|---------------|
| Prompt overhead | system_prompt_tokens / total_input | PM prompt burden |
| Compounding factor | input[last_turn] / input[first_turn] | Context growth |
| Delegation tax | agent_spawn_cost / total_tokens | Overhead per delegation |
| Optimization potential | (pm_prompt * turns * 0.7) + (agent_prompts * delegations * 0.6) | Room to improve |

## Quality Scoring

### Rubric Dimensions (from pilot study)

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Correctness | 20% | All requirements met, correct behavior |
| Code Quality | 15% | Clean code, type hints, naming |
| Architecture | 20% | Separation of concerns, patterns, modularity |
| Testing | 15% | Coverage, edge cases, test quality |
| Error Handling | 15% | Validation, error responses, resilience |
| Documentation | 5% | README, API docs, code comments |
| Docker | 10% | Dockerfile, compose, volumes, env vars |

### Scoring Scale

- 1 = Missing or broken
- 2 = Present but significant issues
- 3 = Good, minor issues
- 4 = Very good, complete
- 5 = Excellent, exceeds expectations

### Pilot Results

| Agent | Tokens | Cost | Quality Score |
|-------|--------|------|---------------|
| claude-mpm (caveman) | 5.5M | $4.42 | 4.40/5 |
| claude-code (verbose) | 10.4M | $6.74 | 3.75/5 |
| codex (baseline) | 1.2M | $0.30 | 4.60/5 |

The caveman prompt delivered 17% better quality at 34% lower cost compared
to the verbose prompt on the same underlying model and task.

## Red Flags (Quality Regression Indicators)

Watch for these signals that compression has gone too far:

### Hard Failures

- Agent misroutes tasks (wrong agent selected)
- Prohibition violations increase (circuit breakers fire more)
- Missing workflow phases (skipping research, QA, etc.)
- Wrong tool names used (compressed names don't match MCP registry)

### Soft Degradation

- Agent asks for clarification more often (ambiguous instructions)
- Delegation descriptions become vague (agent doesn't know what to do)
- Error handling quality drops (fewer edge cases covered)
- Test count decreases (less thorough testing)
- Documentation quality drops (less context in README/comments)

### Measurement Thresholds

| Metric | Acceptable | Warning | Rollback |
|--------|-----------|---------|----------|
| Quality score delta | >= -0.2 | -0.2 to -0.5 | < -0.5 |
| Circuit breaker rate | No increase | 1-2 more/session | >3 more/session |
| Task completion rate | 100% | 90-99% | <90% |
| Agent clarification rate | No increase | 1-2 more/session | >3 more/session |

## Running a Comparison

### Quick Comparison (30 minutes)

```bash
# 1. Capture verbose baseline
git checkout main
# Run test task, note session ID

# 2. Capture caveman
git checkout feat/caveman-prompt
# Run same test task, note session ID

# 3. Compare token usage
python analysis/analyze.py --compare \
  ~/.claude/projects/*/SESSION_A.jsonl \
  ~/.claude/projects/*/SESSION_B.jsonl

# 4. Manual quality review using rubric above
```

### Full Comparison (2-3 hours)

Run 3 different tasks on both prompts:
1. Simple task (e.g., "add a health endpoint")
2. Medium task (e.g., "implement user authentication")
3. Complex task (e.g., "Weather Alerting Service")

Compare aggregate metrics across all 3 tasks. This reduces variance from
task-specific factors.

## Interpreting Results

### Ideal Outcome

- Tokens decreased significantly (>30%)
- Cost decreased proportionally
- Quality score unchanged or improved
- No new circuit breaker violations
- Cache hit rate improved (smaller static prompt = better caching)

### Acceptable Outcome

- Tokens decreased moderately (15-30%)
- Quality score within -0.2 of baseline
- No hard failures
- Minor increase in clarification requests

### Rollback Required

- Quality score drops by >0.5
- Circuit breaker violations increase
- Task completion rate drops below 90%
- Agents consistently misroute or misinterpret tasks
