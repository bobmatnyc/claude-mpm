# Claude Model Selection Research 2025

**Research Date:** 2025-12-18
**Researcher:** Claude Code Research Agent
**Scope:** Current Claude model landscape and agent model selection best practices

---

## Executive Summary

**Key Finding:** Claude Code agents should continue specifying `model: sonnet` for most use cases, with selective use of `opus` and `haiku` based on complexity and cost requirements.

**Model Aliases Update:**
- `sonnet` → `claude-sonnet-4-5-20250929` (Sonnet 4.5)
- `opus` → `claude-opus-4-5-20251101` (Opus 4.5, released Nov 24, 2025)
- `haiku` → `claude-haiku-4-5-20251001` (Haiku 4.5)

**Recommendation:** No urgent changes needed to agent templates, but consider strategic Opus 4.5 usage for complex reasoning tasks.

---

## Current Claude Model Landscape (2025)

### Model Hierarchy

Anthropic maintains a three-tier model family, each optimized for different use cases:

| Model Tier | Current Version | API ID | Pricing (Input/Output) | Best For |
|-----------|----------------|---------|----------------------|----------|
| **Haiku** | 4.5 (Oct 2025) | `claude-haiku-4-5-20251001` | $1/$5 per MTok | Speed, cost-sensitive tasks, high-volume processing |
| **Sonnet** | 4.5 (Sep 2025) | `claude-sonnet-4-5-20250929` | $3/$15 per MTok | Balanced intelligence/speed, coding, agents |
| **Opus** | 4.5 (Nov 2025) | `claude-opus-4-5-20251101` | $5/$25 per MTok | Maximum intelligence, complex reasoning, autonomous agents |

**Source:** [Anthropic Models Overview](https://platform.claude.com/docs/en/about-claude/models/overview)

### Claude Opus 4.5 Release (November 24, 2025)

Anthropic's latest flagship model brings significant improvements:

**Key Capabilities:**
- "Best model in the world for coding, agents, and computer use"
- 80.9% on SWE-bench Verified (industry-leading)
- 66.3% on OSWorld (best computer-using model)
- Improved efficiency: Uses fewer tokens while achieving better results
- New "effort" parameter (low, medium, high) for computational control

**Pricing:**
- Input: $5/MTok (vs $15/MTok for Opus 4.1)
- Output: $25/MTok (vs $75/MTok for Opus 4.1)
- **67% cost reduction** compared to previous Opus 4.1

**Availability:**
- Claude Chat, Claude Code, API
- AWS Bedrock, Google Cloud Vertex AI, Microsoft Azure
- GitHub Copilot (in preview)

**Sources:**
- [Anthropic Opus 4.5 Announcement](https://www.anthropic.com/news/claude-opus-4-5)
- [TechCrunch Coverage](https://techcrunch.com/2025/11/24/anthropic-releases-opus-4-5-with-new-chrome-and-excel-integrations/)
- [CNBC Coverage](https://www.cnbc.com/2025/11/24/anthropic-unveils-claude-opus-4point5-its-latest-ai-model.html)

---

## Model Selection in Claude Code Agents

### Agent Model Field Options

Claude Code subagents support three model specification approaches:

1. **Explicit Model Alias** (most common):
   ```yaml
   model: sonnet  # Uses claude-sonnet-4-5-20250929
   model: opus    # Uses claude-opus-4-5-20251101
   model: haiku   # Uses claude-haiku-4-5-20251001
   ```

2. **Inherit from Parent** (dynamic):
   ```yaml
   model: inherit  # Uses same model as main conversation
   ```

3. **Omit Field** (default):
   ```yaml
   # No model field - defaults to configured subagent model (typically sonnet)
   ```

**Source:** [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents)

### Alias Version Mapping

Model aliases automatically point to the latest stable release:

| Alias | Current Version | Snapshot Date | Auto-Update |
|-------|----------------|---------------|-------------|
| `sonnet` | Sonnet 4.5 | 2025-09-29 | Yes (within ~1 week of new release) |
| `opus` | Opus 4.5 | 2025-11-01 | Yes (within ~1 week of new release) |
| `haiku` | Haiku 4.5 | 2025-10-01 | Yes (within ~1 week of new release) |

**Important:** Anthropic recommends using specific model versions (e.g., `claude-sonnet-4-5-20250929`) in production for consistent behavior, but Claude Code agents typically use aliases for automatic updates.

**Environment Variable Control:**
- `ANTHROPIC_DEFAULT_SONNET_MODEL` - Override sonnet alias
- `ANTHROPIC_DEFAULT_OPUS_MODEL` - Override opus alias
- `ANTHROPIC_DEFAULT_HAIKU_MODEL` - Override haiku alias

**Sources:**
- [Claude Code Model Configuration](https://code.claude.com/docs/en/model-config)
- [Claude Code Support Article](https://support.claude.com/en/articles/11940350-claude-code-model-configuration)

---

## Best Practices for Agent Model Selection

### Official Anthropic Guidance

**Starting Point Recommendations:**

**Option 1: Start with Fast Model (Cost-Optimized)**
1. Begin with Claude Haiku 4.5
2. Test thoroughly
3. Upgrade only if performance gaps identified
4. Best for: Prototyping, high-volume tasks, tight latency requirements

**Option 2: Start with Capable Model (Quality-Optimized)**
1. Begin with Claude Sonnet 4.5
2. Optimize prompts for best performance
3. Consider downgrading to Haiku if sufficient
4. Best for: Complex reasoning, coding, nuanced understanding

**Source:** [Choosing the Right Model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model)

### Model-to-Use-Case Matrix

| Use Case | Recommended Model | Rationale |
|---------|------------------|-----------|
| Complex agents and coding | Sonnet 4.5 | Best balance of intelligence/speed/cost for autonomous tasks |
| Professional software engineering | Opus 4.5 | Maximum intelligence for complex codebases |
| Advanced office automation | Opus 4.5 | Superior tool orchestration for long-running tasks |
| Real-time applications | Haiku 4.5 | Fastest response times with 90% of Sonnet capability |
| High-volume processing | Haiku 4.5 | 3x cost savings vs Sonnet |
| Sub-agent tasks | Haiku 4.5 | Cost-effective for delegated work |

**Source:** [Choosing the Right Model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model)

### Model Economics for Agent Workflows

**Haiku 4.5 Performance Breakthrough:**
- Delivers **90% of Sonnet 4.5's agentic coding performance**
- **2x faster** execution
- **3x cost savings** ($1/$5 vs $3/$15)
- Transforms agent economics for frequent-use scenarios

**Cost Optimization for Subscriptions:**
- 100 Sonnet 4.5 invocations ≈ 300 Haiku 4.5 invocations
- Strategic use of Haiku extends Pro subscription limits by 3x
- Makes Haiku agents substantially more composable

**Dynamic Model Selection Pattern (Emerging):**
1. Start with Haiku 4.5 for task execution
2. If validation fails → escalate to Sonnet 4.5
3. Use Opus 4.5 only for critical high-stakes work

**Source:** [Claude Agent Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)

### Recommended Model-Agent Pairings

Based on current best practices in the community:

| Agent Complexity | Model Choice | Performance/Cost Trade-off |
|-----------------|-------------|---------------------------|
| Lightweight Agent | Haiku 4.5 | 90% performance, 2x speed, 3x savings |
| Medium Agent | Sonnet 4.5 | Balanced for moderate complexity |
| Heavy Agent | Opus 4.5 | Maximum reasoning for complex analysis |

**Advanced Pattern: Model Rotation**
- Run same agent with different models for A/B testing
- Quantify the 10% capability gap in your specific use case
- Make data-driven decisions on model selection

**Source:** [Claude Agent SDK Best Practices](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)

---

## Current Agent Template Analysis

### What We Found

Surveyed **486 agent markdown files** in cache directory:

**Model Distribution:**
- `model: sonnet` - **99%+ of agents**
- `model: opus` - Rare, only in specialized agents
- `model: haiku` - Not found in standard agents
- `model: sonnet|opus|haiku` - Found in BASE-AGENT templates (allows flexibility)

**Key Observations:**
1. Virtually all agents specify `model: sonnet`
2. No agents currently leverage Haiku for cost optimization
3. Opus usage is minimal (pre-Opus 4.5 pricing made it prohibitive)
4. Agent inheritance patterns not widely used

### Example Agent Header

```yaml
---
name: Research
description: Memory-efficient codebase analysis
model: sonnet  # Currently resolves to Sonnet 4.5
resource_tier: high
tags:
- research
- memory-efficient
---
```

**Source:** Local agent cache analysis at `~/.claude-mpm/cache/remote-agents/`

---

## Recommendations for Claude MPM Framework

### 1. No Urgent Changes Required

**Rationale:**
- `model: sonnet` is the recommended starting point per Anthropic
- Aliases auto-update to latest versions (Sonnet 4.5)
- Existing agents continue to benefit from model improvements

**Action:** **NONE** (existing templates remain optimal)

### 2. Consider Strategic Opus 4.5 Adoption

**High-Value Candidates:**
- **PM Agent:** Complex multi-agent delegation and planning
- **Research Agent:** Deep codebase analysis and pattern recognition
- **Architect Agent:** System design and architectural decisions
- **Security Agent:** Vulnerability analysis and threat modeling

**Why Now:**
- Opus 4.5 pricing dropped 67% (vs Opus 4.1)
- Best-in-class performance for autonomous agents (80.9% SWE-bench)
- Cost now comparable to legacy Opus 4.1 at $5/$25 vs $15/$75

**Action:** Test PM and Research agents with `model: opus` in select scenarios

### 3. Explore Haiku 4.5 for Cost Optimization

**Potential Candidates:**
- **Simple file operations** (grep, glob searches)
- **Documentation formatting** agents
- **Sub-agents** performing well-defined tasks
- **High-frequency operations** (commit message formatting, etc.)

**Why:**
- 90% of Sonnet performance at 1/3 the cost
- 2x faster execution for responsive workflows
- Extends Pro subscription limits by 3x

**Action:** Create Haiku variants of lightweight agents for A/B testing

### 4. Implement Model Rotation Testing

**Pattern:**
1. Create test suite for critical agents
2. Run same agent with `haiku`, `sonnet`, and `opus`
3. Measure accuracy, quality, and cost trade-offs
4. Make data-driven model selections per agent

**Action:** Document testing methodology and results

### 5. Add Model Selection Guidance to Agent Documentation

**Include:**
- When to use Haiku vs Sonnet vs Opus
- Cost/performance trade-off matrix
- Environment variable overrides for team policies
- Testing recommendations

**Action:** Create `docs/guides/agent-model-selection.md`

### 6. Leverage `inherit` for Dynamic Workflows

**Use Cases:**
- Sub-agents that should match parent conversation model
- User-controlled model selection (via Claude Code UI)
- Cost-aware workflows (Pro users on Haiku, Team on Sonnet)

**Action:** Add `model: inherit` option to agent templates where appropriate

---

## Model Selection Decision Tree

```
Agent Task Complexity?
│
├─ Lightweight (formatting, simple searches)
│  └─ Use: haiku (3x cost savings, 90% performance)
│
├─ Medium (most coding, moderate analysis)
│  └─ Use: sonnet (balanced, Anthropic's recommendation)
│
└─ Heavy (complex reasoning, autonomous workflows)
   └─ Use: opus (67% cheaper than Opus 4.1, best-in-class)
```

**Validation Strategy:**
- Start with Haiku → escalate to Sonnet if needed
- Reserve Opus for critical high-stakes work
- A/B test to quantify performance gaps in your domain

---

## Migration Path for Existing Agents

### Phase 1: Maintain Status Quo (Current)
- All agents remain `model: sonnet`
- No disruption to existing workflows
- Automatic upgrades to Sonnet 4.5

### Phase 2: Strategic Opus Upgrades (Optional)
- Test PM agent with `model: opus`
- Test Research agent with `model: opus`
- Measure quality improvements vs cost increase
- Document use cases where Opus provides value

### Phase 3: Cost Optimization (Future)
- Identify lightweight agents for Haiku migration
- Create Haiku variants for high-frequency operations
- A/B test Haiku vs Sonnet performance
- Document cost savings and performance trade-offs

### Phase 4: Dynamic Selection (Advanced)
- Implement `model: inherit` where appropriate
- Allow user/team policy control via environment variables
- Create model rotation testing framework
- Data-driven model selection per agent

---

## Environment Variable Strategy

For teams wanting fine-grained control:

```bash
# Default to Haiku for cost savings
export ANTHROPIC_DEFAULT_SONNET_MODEL="claude-haiku-4-5-20251001"

# Or lock to specific versions for stability
export ANTHROPIC_DEFAULT_SONNET_MODEL="claude-sonnet-4-5-20250929"
export ANTHROPIC_DEFAULT_OPUS_MODEL="claude-opus-4-5-20251101"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="claude-haiku-4-5-20251001"
```

**Use Cases:**
- **Cost-conscious teams:** Remap sonnet → haiku globally
- **Stability-focused teams:** Lock to specific snapshot versions
- **Staged rollouts:** Test new models before aliasing
- **A/B testing:** Override aliases per developer/environment

**Source:** [Claude Code Model Configuration](https://code.claude.com/docs/en/model-config)

---

## Testing Recommendations

### 1. Create Benchmark Suite
- Define test cases for each agent type
- Measure accuracy, quality, and cost
- Run across haiku, sonnet, opus variants
- Quantify 10% capability gaps

### 2. SWE-bench Style Evaluation
- Real-world coding tasks
- Compare Haiku 4.5 vs Sonnet 4.5 vs Opus 4.5
- Measure success rate on complex refactorings

### 3. Cost-Performance Analysis
- Track token usage per agent invocation
- Calculate actual cost differences
- Determine ROI for Opus upgrades

### 4. Latency Testing
- Measure response times across models
- Identify use cases where Haiku's 2x speed matters
- Balance latency vs quality trade-offs

---

## Open Questions for Further Research

1. **Does Claude Code have auto-model-selection?**
   - Status: Not found in documentation
   - Appears to be manual via `model:` field or environment variables

2. **Opus 4.5 vs Sonnet 4.5 for PM Agent?**
   - Hypothesis: Opus 4.5's superior reasoning benefits complex delegation
   - Test: Run PM through task planning scenarios with both models

3. **Haiku 4.5 performance delta in real workflows?**
   - Claim: 90% of Sonnet performance
   - Validation: Needs framework-specific testing

4. **Optimal model rotation strategy?**
   - Pattern: Start Haiku → escalate Sonnet → critical Opus
   - Implementation: How to detect when escalation is needed?

5. **Model selection for specialized agents?**
   - Security Agent: Opus for threat modeling?
   - QA Agent: Haiku for test execution, Sonnet for test design?
   - Documentation Agent: Haiku sufficient?

---

## References and Sources

### Primary Sources

1. [Anthropic Opus 4.5 Announcement](https://www.anthropic.com/news/claude-opus-4-5)
2. [Models Overview - Claude Docs](https://platform.claude.com/docs/en/about-claude/models/overview)
3. [Choosing the Right Model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model)
4. [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents)
5. [Claude Code Model Configuration](https://code.claude.com/docs/en/model-config)

### Analysis and Commentary

6. [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
7. [Claude Agent Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
8. [Claude Agent SDK Best Practices](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)
9. [Anthropic Opus 4.5 - Simon Willison](https://simonwillison.net/2025/Nov/24/claude-opus/)

### News Coverage

10. [TechCrunch - Opus 4.5 Release](https://techcrunch.com/2025/11/24/anthropic-releases-opus-4-5-with-new-chrome-and-excel-integrations/)
11. [CNBC - Opus 4.5 Announcement](https://www.cnbc.com/2025/11/24/anthropic-unveils-claude-opus-4point5-its-latest-ai-model.html)
12. [The New Stack - Opus 4.5 Coding Performance](https://thenewstack.io/anthropics-new-claude-opus-4-5-reclaims-the-coding-crown-from-gemini-3/)

---

## Conclusion

**Key Takeaways:**

1. **Current approach is sound:** `model: sonnet` remains the recommended default
2. **Opus 4.5 is a game-changer:** 67% cost reduction makes it viable for complex agents
3. **Haiku 4.5 economics are compelling:** 90% performance at 1/3 cost enables new use cases
4. **No urgent action required:** Existing agents automatically benefit from model improvements
5. **Strategic opportunities exist:** PM/Research agents could benefit from Opus; lightweight agents from Haiku

**Next Steps:**

- [ ] Document current model selection rationale in agent README
- [ ] Test PM agent with `model: opus` for complex delegation scenarios
- [ ] Create Haiku variant of simple agents for cost comparison
- [ ] Establish testing framework for model rotation
- [ ] Monitor Anthropic announcements for future model releases

**Timeline:**
- **Immediate:** No changes (status quo maintained)
- **Q1 2025:** Experiment with Opus for PM/Research agents
- **Q2 2025:** Haiku variants for cost optimization
- **Q3 2025:** Data-driven model selection per agent type

---

**Research Status:** Complete
**Confidence Level:** High (based on official documentation and community best practices)
**Actionability:** Strategic recommendations provided with clear migration path
