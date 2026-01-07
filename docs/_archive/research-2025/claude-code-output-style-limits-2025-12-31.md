---
title: Claude Code Output Style Size Limits Research
date: 2025-12-31
researcher: Claude (Research Agent)
status: Completed
tags: [claude-code, output-styles, limits, system-prompt]
---

# Claude Code Output Style Size Limits Research

## Executive Summary

**Key Finding**: Claude Code has **no documented hard size limit** for output styles, but best practices suggest keeping them under 2,000 characters. Our 58KB teacher style (58,771 characters, ~16,792 tokens) significantly exceeds recommended guidelines.

**Recommendation**: Condense the claude-mpm-teacher.md output style to under 10,000 characters (approximately 2,857 tokens) for optimal performance.

---

## Research Questions

1. Is there a documented size limit for output styles?
2. Are there reports of large styles failing to load?
3. What's the recommended maximum size?
4. How does output style size impact Claude Code performance?

---

## Findings

### 1. No Hard Size Limit Documented

**Sources:**
- [Official Output Styles Documentation](https://code.claude.com/docs/en/output-styles)
- [Claude Code GitHub Repository](https://github.com/anthropics/claude-code)
- Multiple community guides and tutorials

**Finding:** None of the official documentation or community resources specify a hard size limit for output style files. The format is simply described as "Markdown files with frontmatter and text that will be added to the system prompt."

### 2. Best Practice Recommendation: Under 2,000 Characters

**Source:** [Shipyard Blog - Pair Programming with Claude Code](https://shipyard.build/blog/claude-code-output-styles-pair-programming/)

**Quote:** "Check file length: Report the file size in characters/tokens to ensure it's reasonable for a system prompt (aim for under 2000 characters)."

**Analysis:**
- This is the **only documented guideline** found during research
- Appears to be community best practice rather than official Anthropic guidance
- Suggests output styles should be concise and focused

### 3. Current File Sizes

**claude-mpm-teacher.md:**
- Size: 58,771 characters (58KB)
- Words: 8,580 words
- Estimated tokens: ~16,792 tokens (using 3.5 chars/token heuristic)
- **29.4x over recommended limit** (58,771 ÷ 2,000)

**claude-mpm.md (working fine):**
- Size: 12,149 characters (12KB)
- **6.1x over recommended limit** (12,149 ÷ 2,000)
- Still loads and works properly

### 4. Token Estimation

**Anthropic Guidance:** ([Token Counting Documentation](https://docs.claude.com/en/docs/build-with-claude/token-counting))
- **Official heuristic**: 1 token ≈ 3.5 English characters
- **Alternative estimate**: 1 token ≈ 0.75 words (or 1.33 tokens/word)

**Calculations for claude-mpm-teacher.md:**

| Method | Calculation | Estimated Tokens |
|--------|-------------|------------------|
| Character-based | 58,771 ÷ 3.5 | ~16,792 tokens |
| Word-based | 8,580 × 1.33 | ~11,411 tokens |
| Average | (16,792 + 11,411) ÷ 2 | ~14,102 tokens |

**Context:** Claude Sonnet 4 has a 200,000 token context window with 64,000 output tokens. A 16,792 token output style consumes **~8.4% of the total context window** before any user input.

### 5. GitHub Issues Analysis

**Relevant Issues Found:**

1. **[Issue #1452](https://github.com/anthropics/claude-code/issues/1452)**: Large file mention hangs Claude Code
   - **Impact**: Memory issues when processing very large files (20GB+)
   - **Relevance**: Not directly related to output styles, but shows Claude Code can struggle with large inputs

2. **[Issue #6450](https://github.com/anthropics/claude-code/issues/6450)**: Output Styles Ignored by Claude Code
   - **Impact**: Output styles may be overridden by Claude's training patterns
   - **Relevance**: Suggests that even well-crafted output styles may not always be followed
   - **Implication**: Larger styles may be even more likely to be partially ignored

3. **[Issue #10721](https://github.com/anthropics/claude-code/issues/10721)**: Keep output-style feature
   - **Status**: Output styles were deprecated in v2.0.30 but un-deprecated based on community feedback
   - **Current Status**: Output styles are still supported as of late 2025

4. **[Issue #7679](https://github.com/anthropics/claude-code/issues/7679)**: Increase file token limit from 25,000 to 50,000
   - **Context**: Claude Code has a 25,000 token limit for reading individual files
   - **Relevance**: Suggests token limits are actively managed in Claude Code
   - **Implication**: Large output styles may face similar constraints

### 6. System Prompt Integration

**How Output Styles Work:**
- Output styles **replace** the default Claude Code system prompt
- They are loaded at session start and added to the system message
- Custom output styles exclude coding instructions unless `keep-coding-instructions: true` is set in frontmatter

**Performance Implications:**
- Larger output styles consume more context window tokens
- Reduce available space for conversation history and tool outputs
- May increase API costs (more input tokens per request)
- Could impact response quality if style is too verbose or unfocused

### 7. Community Examples

**Source:** [Awesome Claude Code Output Styles Repository](https://github.com/hesreallyhim/awesome-claude-code-output-styles-that-i-really-like)

**Example Styles:** All examples in the repository are concise (typically 500-2000 characters):
- technical-evangelist.md
- zen-master.md
- haiku-helper.md
- existentialist-poet.md

**Observation:** Community-created output styles follow the "concise and focused" pattern, aligning with the 2,000 character guideline.

### 8. No Error Logs Found

**Search Results:**
- Examined ~/.claude/debug/ directory (42,055+ debug files)
- Searched for references to "output-style", "output style", or "claude-mpm-teacher"
- **No errors or warnings found related to output style loading**

**Conclusion:** The teacher style appears to load without errors, but size may still impact performance in subtle ways.

---

## Analysis and Implications

### Why Large Output Styles May Be Problematic

1. **Context Window Consumption**
   - 16,792 tokens for system prompt is significant
   - Leaves less room for conversation history and tool outputs
   - May trigger context truncation in long sessions

2. **Adherence Issues**
   - Issue #6450 shows Claude may ignore output style guidance
   - Larger styles with many instructions may be harder for Claude to follow consistently
   - More surface area for conflicts with Claude's base training

3. **Performance Impact**
   - Every request includes the full output style in the system prompt
   - Longer prompts = higher latency and API costs
   - May slow down response generation

4. **Maintenance Burden**
   - Harder to update and modify large styles
   - More difficult for users to understand what the style does
   - Increased chance of conflicting or redundant instructions

### Comparison to Working Style

**claude-mpm.md (12KB, working fine):**
- Still 6x over recommended limit
- Suggests Claude Code can handle styles larger than 2,000 characters
- But no guarantee this will remain true in future versions

**claude-mpm-teacher.md (58KB):**
- 29x over recommended limit
- 4.8x larger than the working style
- May be experiencing subtle performance issues not immediately visible

---

## Recommendations

### Immediate Action

**Condense claude-mpm-teacher.md to under 10,000 characters** (~2,857 tokens)

**Target Reduction:** 58,771 → 10,000 characters (83% reduction)

**Strategies:**
1. **Remove redundant content**: Identify overlapping instructions
2. **Prioritize core functionality**: Keep only essential teaching behaviors
3. **Use concise language**: Eliminate verbose explanations
4. **Reference external docs**: Link to detailed guides instead of including full text
5. **Leverage CLAUDE.md**: Move project-specific context to CLAUDE.md instead of output style

### Long-Term Best Practices

1. **Keep output styles focused**: Each style should have a clear, singular purpose
2. **Test at different sizes**: Monitor performance with styles of varying lengths
3. **Monitor context usage**: Track how much context window is consumed by system prompt
4. **Regular audits**: Periodically review and trim output styles
5. **Modular approach**: Consider splitting complex styles into multiple focused ones

### Alternative Approaches

If the teacher style needs to remain comprehensive:

1. **Use CLAUDE.md for project context**: Move project-specific information out of the output style
2. **Create multiple teacher styles**: Split into "teacher-basic.md", "teacher-advanced.md", etc.
3. **Use plugins or hooks**: Leverage Claude Code's plugin system for complex behaviors
4. **Document externally**: Create detailed documentation and reference it briefly in the style

---

## Token Estimation Reference

### Quick Conversion Table

| Characters | Words | Estimated Tokens (3.5 char/token) | Estimated Tokens (1.33 token/word) |
|------------|-------|-----------------------------------|-------------------------------------|
| 2,000 | 286 | 571 | 380 |
| 5,000 | 714 | 1,429 | 950 |
| 10,000 | 1,429 | 2,857 | 1,900 |
| 20,000 | 2,857 | 5,714 | 3,800 |
| 50,000 | 7,143 | 14,286 | 9,500 |
| 58,771 | 8,580 | 16,792 | 11,411 |

**Note:** Actual token counts may vary. Use [Claude Tokenizer](https://claude-tokenizer.vercel.app/) for precise measurements.

---

## Sources

### Official Documentation
- [Output Styles - Claude Code Docs](https://code.claude.com/docs/en/output-styles)
- [Token Counting - Claude Docs](https://docs.claude.com/en/docs/build-with-claude/token-counting)
- [Claude Tokenizer](https://claude-tokenizer.vercel.app/)

### GitHub Issues
- [Issue #1452: Large file mention hangs Claude Code](https://github.com/anthropics/claude-code/issues/1452)
- [Issue #6450: Output Styles Ignored by Claude Code](https://github.com/anthropics/claude-code/issues/6450)
- [Issue #7679: Increase file token limit](https://github.com/anthropics/claude-code/issues/7679)
- [Issue #10721: Keep output-style feature](https://github.com/anthropics/claude-code/issues/10721)

### Community Resources
- [Shipyard Blog - Pair Programming with Claude Code](https://shipyard.build/blog/claude-code-output-styles-pair-programming/)
- [Awesome Claude Code Output Styles Repository](https://github.com/hesreallyhim/awesome-claude-code-output-styles-that-i-really-like)
- [Awesome Claude Code Repository](https://github.com/hesreallyhim/awesome-claude-code)

### Technical References
- [Understanding Usage and Length Limits - Claude Help Center](https://support.claude.com/en/articles/11647753-understanding-usage-and-length-limits)
- [Claude Code Limits Explained (2025 Edition)](https://www.truefoundry.com/blog/claude-code-limits-explained)

---

## Next Steps

1. **Audit claude-mpm-teacher.md**: Identify sections that can be condensed or removed
2. **Create condensed version**: Target 10,000 characters or less
3. **Test both versions**: Compare behavior and performance
4. **Monitor context usage**: Track token consumption in actual usage
5. **Document decisions**: Record what was kept vs. removed and why
6. **Consider alternatives**: Evaluate using CLAUDE.md or plugins for complex behaviors

---

## Conclusion

While Claude Code has no hard documented size limit for output styles, the 58KB teacher style significantly exceeds community best practices (2,000 characters). The size likely impacts:

- **Context window efficiency**: Consuming ~8.4% of available tokens
- **Response quality**: Potential for instruction conflicts and inconsistent adherence
- **Performance**: Higher latency and API costs
- **Maintainability**: Difficult to update and understand

**Recommendation**: Condense the teacher style to under 10,000 characters (approximately 17% of current size) to align with best practices while retaining core functionality.

The working 12KB style proves Claude Code can handle larger-than-recommended styles, but pushing to 58KB may introduce subtle issues not immediately apparent. A more focused, concise style will likely perform better and be easier to maintain.
