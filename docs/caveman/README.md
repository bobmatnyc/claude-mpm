# Caveman Prompt Optimization

Token-efficient prompt engineering for Claude MPM. Reduces system prompt tokens
by 77% while preserving all functional rules and improving output quality.

## What is Caveman Prompting?

Terse, table-driven system prompts that preserve meaning in fewer tokens.
LLMs trained on enough language to infer full meaning from compressed signals.
Based on Microsoft's LLMLingua research (arXiv:2310.05736): 20x compression
with <2% accuracy loss.

## Results

| Metric | Before (verbose) | After (caveman) | Delta |
|--------|------------------|-----------------|-------|
| PM_INSTRUCTIONS.md | 47KB / 1142 lines / ~12.7K tokens | 10.8KB / 234 lines / ~2.7K tokens | **-77%** |
| BASE_PM.md | 3.8KB / 72 lines / ~947 tokens | 1.4KB / 33 lines / ~348 tokens | **-63%** |
| Pilot cost | $6.74 | $4.42 | **-34%** |
| Pilot tokens | 10.4M | 5.5M | **-47%** |
| Pilot quality | 3.75/5 | 4.40/5 | **+17%** |

Quality measured on Weather Alerting Service challenge (Level 3) evaluated by
QA agent using rubric scoring across correctness, architecture, testing, error
handling, documentation, and Docker.

## Documentation

- [Techniques Guide](techniques.md) -- Compression techniques with before/after examples
- [Agent Communication](agent-communication.md) -- Symbolic formats for agent-to-agent messaging
- [Measurement Guide](measurement.md) -- How to measure and validate prompt changes
- [Style Guide](style-guide.md) -- Rules for writing caveman-style prompts
- [Roadmap](roadmap.md) -- Future optimization phases

## Key Insight

Quality does NOT correlate with cost. In the pilot study, the cheapest agent
(codex, ~$0.30) produced the highest quality implementation (4.60/5), while
the most expensive (claude-code, $6.74) ranked third (3.75/5). Token
efficiency and model capability matter more than raw token volume.

## References

- LLMLingua (arXiv:2310.05736) -- 20x compression, 1.5-point accuracy loss
- LLMLingua-2 (arXiv:2403.12968) -- 2-5x compression, faster, better generalization
- MetaGPT (arXiv:2308.00352) -- Structured formats reduce cascading hallucinations
- Anthropic prompt caching docs -- 90% cost reduction on cached portions
