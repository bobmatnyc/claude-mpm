# Optimization Roadmap

Future phases beyond the initial caveman prompt rewrite (Phase 1).

## Status Overview

| Phase | Status | Token Impact | Cost Impact |
|-------|--------|-------------|-------------|
| Phase 1: Caveman Rewrite | **COMPLETE** | -77% PM prompt | -34% session cost |
| Phase 2: Progressive Disclosure | Planned | ~6K/delegation | ~$1.08/session |
| Phase 3: Agent Def Compression | Planned | ~25K total | ~$0.50/session |
| Phase 4: Prompt Caching | Planned | ~30M cache reads | ~$13/session |
| Phase 5: Agent Communication | Proposed | ~5K/session | Negligible |

**Combined target**: 87M tokens ($49) baseline -> 56M ($33) without caching,
$10-15 with perfect caching.

## Phase 1: Caveman Prompt Rewrite (COMPLETE)

Applied all 6 compression techniques to PM_INSTRUCTIONS.md:

| Technique | Savings Applied |
|-----------|----------------|
| Remove filler/hedging | ~15% |
| Merge duplicate rules (4 -> 1 table) | ~20% |
| Tables instead of prose | ~25% |
| Remove obvious instructions | ~10% |
| Compress agent catalog (618 -> ~60 lines) | ~30% |
| Symbolic notation (CB#, P#, ->) | ~5% |

Result: 47KB / 1142 lines -> 10.8KB / 234 lines (-77%)

Pilot validation: Quality improved from 3.75/5 to 4.40/5 on Weather
Alerting Service challenge.

## Phase 2: Progressive Disclosure

**Goal**: Move rarely-used content from always-loaded prompts to on-demand
skills, loaded only when context triggers match.

### 2a. Extract Git Workflow from BASE_AGENT

- **Source**: `src/claude_mpm/agents/BASE_AGENT.md` (git sections, ~150 lines)
- **Target**: `plugin/skills/universal-collaboration-git-workflow/` (exists)
- **Savings**: ~500 tokens per agent spawn
- **Trigger**: Detected when git operations mentioned in task

### 2b. Extract Code Quality Patterns from BASE_AGENT

- **Source**: `src/claude_mpm/agents/BASE_AGENT.md` (quality sections, ~120 lines)
- **Target**: Merge into `plugin/skills/universal-architecture-software-patterns/`
- **Savings**: ~400 tokens per agent spawn
- **Trigger**: Detected when refactoring/quality mentioned in task

### 2c. Extract Ticket Protocol from Research Agent

- **Source**: `.claude/agents/research.md` (ticket sections, ~400 lines, ~5K tokens)
- **Target**: `plugin/skills/mpm-ticketing-integration/` (exists)
- **Savings**: ~5K tokens per Research delegation
- **Trigger**: Ticket IDs or issue URLs in task context

### 2d. Implement Skill Loading Triggers

- **File**: `src/claude_mpm/agents/agent_loader.py`
- **What**: Ensure `get_agent_prompt()` only appends skill content when task
  context matches triggers, not unconditionally
- **Dependencies**: 2a-2c must be extracted first

### Estimated Impact

~6K tokens saved per delegation x 10 delegations = 60K tokens/session (~$0.18)

## Phase 3: Agent Definition Compression

**Goal**: Apply caveman techniques to individual agent definitions.

### Targets

| Agent | Current (tokens) | Target | Strategy |
|-------|-----------------|--------|----------|
| BASE_AGENT | 2,700 | 1,000-1,200 | Remove generic quality advice |
| research | 19,700 | 6,000-8,000 | Extract ticket/workspace/MCP to skills |
| python-engineer | 15,100 | 4,000-5,000 | Extract algorithm cookbook to skill |
| documentation | 3,500 | 2,000 | Already reasonably sized |
| qa | 2,100 | 1,500 | Minor compression |
| data-scientist | 1,900 | 1,500 | Minor compression |
| code-analyzer | 1,700 | 1,200 | Minor compression |
| local-ops | 637 | 500 | Already minimal |

### Approach

For each agent:
1. Identify content Claude already knows (generic best practices)
2. Identify content that belongs in skills (loaded on-demand)
3. Convert remaining prose to tables
4. Remove filler language
5. A/B test before deploying

### Risk Notes

- Agent definitions have less redundancy than PM prompt (less easy savings)
- Research agent (19.7K) is the biggest target with most extractable content
- python-engineer (15.1K) has large algorithm cookbook that should be a skill
- Smaller agents may not justify optimization effort

### Estimated Impact

~25K tokens total across all agents (~$0.50/session)

## Phase 4: Prompt Caching Optimization

**Goal**: Maximize Anthropic prompt cache hit rates for 90% cost reduction
on static content.

### 4a. Verify Cache-Friendly Message Structure

- **File**: `src/claude_mpm/agents/agent_loader.py`
- **What**: Ensure PM system prompt is placed BEFORE dynamic content in the
  message array. Static content first = cache-friendly
- **Verification**: Check session logs for `cache_read_input_tokens > 0`
  on turn 2+
- **Current state**: First turn shows 49K cache_creation, 0 cache_read.
  Need to verify turn 2+ behavior.

### 4b. Cross-Agent Cache Sharing

- **What**: Investigate whether BASE_AGENT content can share cache across
  agent spawns
- **Hypothesis**: If BASE_AGENT is identical prefix for all agents, it
  should be cacheable across spawns
- **Requirement**: Identical token sequence at the start of each agent prompt
- **Limitation**: Anthropic cache requires exact prefix match

### 4c. Cache Monitoring Dashboard

- **What**: Build monitoring for cache hit rates across sessions
- **Metrics**: cache_read / (input + cache_read) per turn
- **Alert**: If cache hit rate drops below 80% after turn 1

### Estimated Impact

~30M cache reads per session. At $0.30/M vs $3.00/M, this is ~$13/session
savings. This is the single highest-impact optimization.

### Prerequisites

- Phase 1 (smaller prompt = faster cache creation)
- Understanding of Claude Code's message construction

## Phase 5: Agent Communication Protocol (HSDF)

**Goal**: Implement structured delegation format for PM-to-agent messaging.
See [agent-communication.md](agent-communication.md) for full specification.

### Implementation Steps

1. Define YAML schema for HSDF v1
2. Update PM instructions with HSDF templates
3. Update agent definitions to parse structured delegations
4. Update agent definitions to return structured results
5. A/B test delegation quality
6. Deploy with verbose fallback for edge cases

### Estimated Impact

~5K tokens/session. Low absolute impact but improves:
- Delegation clarity (fewer misinterpretations)
- Response parseability (automated result processing)
- Latency (fewer tokens to generate per delegation)

## Priority Order

Ranked by impact-to-effort ratio:

1. **Phase 4: Caching** -- ~$13/session, config-level effort, zero quality risk
2. **Phase 1: Caveman rewrite** -- DONE. 77% prompt reduction, validated quality
3. **Phase 2: Progressive disclosure** -- ~$1.08/session, moderate effort
4. **Phase 3: Agent compression** -- ~$0.50/session, moderate effort, per-agent A/B test
5. **Phase 5: HSDF** -- ~$0/session (negligible cost), improves clarity/latency

## Success Criteria

| Metric | Current | Phase 2 | Phase 3 | Phase 4 | All Phases |
|--------|---------|---------|---------|---------|------------|
| Session tokens | 87M | 82M | 79M | 56M | 56M |
| Session cost | $49 | $47 | $46 | $33 | $10-15* |
| PM prompt size | 2.7K | 2.7K | 2.7K | 2.7K | 2.7K |
| Quality score | 4.40/5 | >= 4.40 | >= 4.40 | >= 4.40 | >= 4.40 |

*With perfect caching on all static content.

## Open Questions

1. **Cache hit rate in practice**: How well does Anthropic cache work with
   Claude Code's message construction? Need empirical measurement.
2. **Progressive disclosure triggers**: How reliably can we detect when a
   skill should be loaded? False negatives mean missing information.
3. **Agent compression limits**: How much can agent prompts be compressed
   before quality degrades? Each agent may have a different floor.
4. **Cross-model applicability**: Do caveman prompts work equally well on
   Haiku vs Sonnet vs Opus? Smaller models may need more explicit guidance.
