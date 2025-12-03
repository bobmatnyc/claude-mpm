# Agent Optimization Patterns Reference

**Purpose**: Quick reference for maintaining professional, explanatory guidance in Claude MPM agents
**Applies To**: All agent files in the framework
**Standard**: Claude 4.5 Professional Guidance

## Core Principles

1. **Guide, Don't Command**: Use guidance-oriented language instead of imperatives
2. **Explain WHY**: Add context explaining the reasoning behind recommendations
3. **Professional Tone**: Maintain clarity without aggressive enforcement
4. **Token Efficiency**: Remove redundancy while preserving meaning
5. **Technical Accuracy**: Preserve all technical content and functionality

## Pattern Transformations

### 1. Aggressive Imperatives → Guidance

| Before | After | Why |
|--------|-------|-----|
| You MUST validate input | Validate input to prevent injection | Explains consequence |
| NEVER expose credentials | Avoid exposing credentials in logs | Explains location concern |
| ALWAYS use HTTPS | Use HTTPS for secure data transmission | Explains purpose |
| CRITICAL: Check auth | Check authentication before API calls | Explains when |
| MANDATORY testing | Testing ensures quality and catches regressions | Explains benefit |
| FORBIDDEN in production | Not recommended for production use | Softer prohibition |
| REQUIRED before deploy | Needed before deployment to ensure stability | Explains timing |
| ESSENTIAL for security | Important for maintaining security standards | Explains priority |

**Pattern**: Replace imperatives with explanatory guidance that includes:
- What to do
- Why it matters
- When/where it applies
- What happens otherwise

### 2. Emoji Pollution → Clean Headers

| Before | After |
|--------|-------|
| ## 🔴 Critical Setup | ## Critical Setup |
| ### ⚠️ Warning: Migrations | ### Caution: Database Migrations |
| ### ✅ Best Practices | ### Best Practices |
| - 🚨 ALWAYS backup | - Backup before migration to prevent data loss |
| - 💡 Use caching | - Use caching to improve response times |
| - ❌ Don't skip tests | - Run tests to catch regressions |

**Pattern**: Remove emojis and improve clarity through:
- Better wording in headers
- Explanatory text in bullet points
- Context about consequences
- Professional terminology

### 3. Code Comment Improvements

**Before:**
```python
# ❌ WRONG - Insecure password storage
password = request.form['password']
db.store(password)

# ✅ CORRECT - Hashed password storage
password = request.form['password']
hashed = bcrypt.hash(password)
db.store(hashed)
```

**After:**
```python
# Problem: Storing plain text passwords exposes user data
password = request.form['password']
db.store(password)

# Solution: Hash passwords to protect user data at rest
password = request.form['password']
hashed = bcrypt.hash(password)
db.store(hashed)
```

**Pattern**: Transform code comments to:
- `# Problem:` instead of `# ❌ WRONG`
- `# Solution:` instead of `# ✅ CORRECT`
- `# Issue:` instead of `# 🔴 BAD`
- `# Better approach:` instead of `# ✅ GOOD`
- `# Note:` instead of `# ⚠️ WARNING`
- Add "what happens" and "why approach differs"

### 4. Warning Transformations

| Before | After |
|--------|-------|
| **WARNING**: Do not X | Caution: Avoid X to prevent Y |
| **IMPORTANT**: Remember X | Note: Remember X for Y reason |
| **DANGER**: X can cause Y | Be careful: X can cause Y, leading to Z |
| **ATTENTION**: Read this | Consider: This approach works because X |

**Pattern**: Convert warnings to explanatory notes that:
- State the concern
- Explain the consequence
- Provide context for the guidance

### 5. Token Efficiency Improvements

**Before:**
```markdown
## Important Warning About Security

⚠️ **CRITICAL SECURITY WARNING**: You MUST ALWAYS validate user input!

This is ESSENTIAL because:
- NEVER trust user input
- ALWAYS sanitize data
- MANDATORY for security
```

**After:**
```markdown
## Input Validation

Validate user input to prevent injection attacks and ensure data integrity.

Why validation matters:
- Prevents SQL injection and XSS attacks
- Ensures data type consistency
- Maintains application security standards
```

**Pattern**: Streamline by:
- Removing redundant emphasis
- Consolidating similar points
- Using lists efficiently
- Eliminating repetitive warnings

## Context Addition Strategies

### When to Add WHY Context

1. **Security patterns**: Explain attack vectors prevented
2. **Performance patterns**: Explain bottlenecks avoided
3. **Testing patterns**: Explain bugs caught
4. **Architecture patterns**: Explain maintainability benefits
5. **Configuration patterns**: Explain environment implications

### Context Examples

**Security:**
```markdown
# Before
NEVER store API keys in code

# After
Avoid storing API keys in code to prevent exposure in version control history
```

**Performance:**
```markdown
# Before
ALWAYS use caching

# After
Use caching to reduce database load and improve response times by 10-100x
```

**Testing:**
```markdown
# Before
MUST write tests

# After
Write tests to catch regressions and ensure expected behavior during refactoring
```

## Anti-Patterns to Avoid

### ❌ Don't Do This
- Using ALL CAPS for emphasis
- Multiple exclamation marks!!!
- Excessive bolding **everywhere**
- Redundant warnings repeated multiple times
- Emojis as visual enforcement
- Aggressive imperatives without context
- "DO NOT" without explanation

### ✅ Do This Instead
- Use clear, descriptive language
- Single emphasis for important points
- Bold for headers and key terms only
- Consolidate similar guidance
- Clean, professional formatting
- Guidance with explanatory context
- "Avoid X because Y" with reasoning

## Quality Checklist

Use this checklist when writing or reviewing agent instructions:

### Tone Check
- [ ] No aggressive imperatives (MUST, NEVER, ALWAYS, CRITICAL)
- [ ] Guidance explains WHY, not just WHAT
- [ ] Professional, educational tone maintained
- [ ] Commands converted to recommendations with context

### Format Check
- [ ] No enforcement emojis (🔴, ⚠️, ✅, ❌, 🚨, 💡, 🎯)
- [ ] Clean headers without visual clutter
- [ ] Code comments use Problem/Solution format
- [ ] Consistent markdown formatting

### Content Check
- [ ] WHY context provided for major patterns
- [ ] Technical accuracy preserved
- [ ] No functionality changes
- [ ] Redundant warnings removed
- [ ] Examples are clear and relevant

### Efficiency Check
- [ ] No repetitive warnings
- [ ] Similar sections consolidated
- [ ] Examples streamlined
- [ ] Token usage optimized without losing meaning

## Category-Specific Guidance

### Base Templates
- Extra care required - changes cascade to inheriting agents
- Set professional tone foundation
- Provide clear inheritance patterns
- Document when to inherit vs. override

### QA Agents
- Maintain testing rigor while improving tone
- Convert "MUST test X" to "Test X to ensure Y"
- Explain why comprehensive coverage matters
- Preserve test strategy frameworks

### Security Agents
- Critical warnings need careful conversion
- Explain attack vectors, not just vulnerabilities
- Maintain urgency without aggression
- Provide context for security patterns

### Mobile Engineers
- Platform-specific constraints require precision
- Explain mobile-specific limitations
- Add context for platform choices
- Preserve technical accuracy for build systems

### Ops Agents
- Deployment concerns need clear explanation
- Explain production implications
- Provide context for infrastructure decisions
- Maintain operational rigor

### Specialized Engineers
- Domain expertise requires technical precision
- Explain domain-specific patterns
- Add context for specialized tools
- Preserve technical terminology

## Examples from Optimized Agents

### Excellent Professional Guidance

**From python-engineer.md:**
```markdown
### Virtual Environment Management

Create isolated Python environments to prevent dependency conflicts between projects.
Each project should use its own virtual environment to ensure reproducible builds.

Why virtual environments matter:
- Isolate project dependencies from system packages
- Enable reproducible builds across environments
- Prevent version conflicts between projects
- Allow testing with different Python versions
```

**From nextjs-engineer.md:**
```markdown
### Server Components by Default

Use React Server Components (RSC) as the default pattern in Next.js 13+ App Router.
They reduce client bundle size and enable server-side data fetching without waterfalls.

Benefits:
- Zero JavaScript sent to client for server components
- Direct database/API access without separate API routes
- Automatic code splitting at component boundaries
- Better SEO through server-side rendering
```

**From security.md:**
```markdown
### Input Validation Strategy

Validate all user input at system boundaries to prevent injection attacks and ensure
data integrity. Use allowlists rather than denylists for validation rules.

Why validation matters:
- Prevents SQL injection, XSS, and command injection
- Ensures data type consistency and business logic constraints
- Reduces attack surface by rejecting invalid input early
- Provides clear error messages for debugging
```

## Migration Guide for New Contributors

When adding new agents or updating existing ones:

1. **Write guidance, not commands**: Focus on "why" and "when", not just "what"
2. **Avoid emojis in instructions**: Use clear language instead of visual enforcement
3. **Explain consequences**: Help Claude understand reasoning, not just rules
4. **Use Problem/Solution**: Format code comments educationally
5. **Review against checklist**: Use the quality checklist above
6. **Test with Claude**: Ensure guidance is clear and actionable

## Validation Tools

### Manual Review
```bash
# Check for aggressive imperatives
grep -r "MUST\|NEVER\|ALWAYS\|CRITICAL\|MANDATORY" agents/

# Check for emoji pollution
grep -r "[🔴⚠️✅❌🚨💡🎯]" agents/

# Check for aggressive code comments
grep -r "# ❌ WRONG\|# ✅ CORRECT" agents/
```

### Automated Validation
```python
# Use the phase4_optimizer.py patterns for automated checking
python scripts/validate_agent_quality.py agents/new-agent.md
```

## Resources

- **Complete Summary**: `/docs/optimization/COMPLETE-OPTIMIZATION-SUMMARY.md`
- **Phase Reports**: `/docs/optimization/phase[1-4]-agent-optimization-report.md`
- **Optimization Script**: `/phase4_optimizer.py` (reference implementation)

---

**Last Updated**: December 3, 2025
**Applies To**: Claude MPM v2.x agent library
**Standard**: Claude 4.5 Professional Guidance
