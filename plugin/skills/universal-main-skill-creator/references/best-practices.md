# Skill Creation Best Practices

## Writing Style and Voice

### Imperative Form (MANDATORY)

All skill content MUST use imperative/infinitive form (verb-first instructions), not second person.

**✅ Correct Examples:**
- "To accomplish X, do Y"
- "Follow these steps to complete the task"
- "Load the reference file when needed"
- "Execute the script with these parameters"
- "Consider these factors before proceeding"

**❌ Incorrect Examples:**
- "You should do X"
- "If you need to do X"
- "You can find this in..."
- "Your task is to..."
- "You will need to..."

**Rationale:**
- Maintains consistency across all skills
- Optimizes for AI comprehension
- Removes ambiguity about audience
- Creates professional, instructional tone
- Easier to scan and parse

### Voice and Tone Guidelines

**Objective and Instructional:**
- Focus on clear procedures and workflows
- State facts and requirements directly
- Avoid conversational filler
- Be specific and actionable

**Active Voice:**
- "Execute the script" not "The script should be executed"
- "Load the reference" not "The reference can be loaded"
- "Validate the input" not "Input should be validated"

**Present Tense:**
- "The skill provides..." not "The skill will provide..."
- "Claude loads..." not "Claude will load..."
- "Scripts execute..." not "Scripts will execute..."

### Documentation Style

**Concise and Scannable:**
- Use bullet points for lists
- Keep paragraphs short (2-4 sentences)
- Use headers to organize content
- Highlight key terms in **bold**
- Use code blocks for examples

**Example-Driven:**
- Show concrete examples
- Demonstrate patterns in practice
- Provide before/after comparisons
- Include realistic scenarios

## Metadata Quality

### Name Field

The `name:` field in YAML frontmatter should be:

**Format:** kebab-case (lowercase with hyphens)

**Examples:**
- ✅ `skill-creator`
- ✅ `mcp-builder`
- ✅ `testing-anti-patterns`
- ❌ `Skill Creator`
- ❌ `skill_creator`
- ❌ `skillCreator`

### Description Field

The `description:` field determines when Claude activates the skill. Write descriptions that:

**Be Specific About Purpose:**
- Clearly state what the skill does
- Mention key capabilities
- Include constraints or limitations

**Use Third Person:**
- "This skill should be used when..." ✅
- "Use this skill when..." ❌
- "The skill provides..." ✅
- "Provides..." ❌

**Include Activation Conditions:**
- What user requests trigger the skill?
- What keywords or scenarios activate it?
- When should it NOT be used?

**Examples:**

✅ **Good:**
```yaml
description: Create high-quality MCP servers that enable LLMs to effectively interact with external services. Use when building MCP integrations for APIs or services in Python (FastMCP) or Node/TypeScript (MCP SDK).
```

❌ **Too Vague:**
```yaml
description: Helps with MCP servers.
```

❌ **Wrong Voice:**
```yaml
description: Use this when you need to build MCP servers.
```

✅ **Good:**
```yaml
description: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.
```

## Content Organization

### Entry Point Structure

For skills using progressive disclosure, organize the entry point with these sections:

1. **Overview** (2-3 sentences)
   - What the skill provides
   - Key capabilities
   - Primary value proposition

2. **When to Use This Skill** (5-10 bullet points)
   - Clear activation scenarios
   - Specific trigger conditions
   - Related keywords

3. **The Iron Law** (Optional, if applicable)
   - Non-negotiable principles
   - Core constraints
   - Fundamental requirements

4. **Core Principles** (3-5 brief principles)
   - Foundational guidelines
   - Key philosophies
   - Essential approaches

5. **Quick Start** (5-10 steps)
   - High-level workflow
   - Phase-based organization
   - Links to detailed references

6. **Navigation** (Annotated list)
   - All reference files
   - Clear descriptions
   - When to load each

7. **Key Reminders** (5-10 bullets)
   - Critical points
   - Common pitfalls
   - Essential practices

8. **Red Flags - STOP** (5-10 warning signs)
   - Anti-patterns to avoid
   - Warning indicators
   - Stop conditions

9. **Integration with Other Skills** (Optional)
   - Related skills
   - Prerequisites
   - Complementary skills

10. **Real-World Impact** (Optional)
    - Metrics and outcomes
    - Evidence of effectiveness
    - Success stories

### Reference File Structure

Each reference file should have:

**Clear Purpose Statement:**
```markdown
# Reference Topic Name

## Purpose

Brief description of what this reference covers and when to use it.
```

**Logical Organization:**
- Clear section hierarchy
- Progressive complexity (simple → advanced)
- Self-contained content
- Cross-references where helpful

**Appropriate Depth:**
- 150-500 lines per file
- Combine if <150 lines
- Split if >500 lines

## Resource Organization

### Scripts Best Practices

**When to Create Scripts:**
- Same code repeatedly rewritten
- Deterministic execution required
- Complex operations benefit from testing
- Performance optimization matters

**Script Quality:**
- Include usage documentation
- Handle errors gracefully
- Support common parameters
- Add helpful error messages
- Make executable (`chmod +x`)

**Documentation in SKILL.md:**
```markdown
Execute `scripts/rotate_pdf.py <input.pdf> <output.pdf> <degrees>` to rotate PDFs.

Parameters:
- input.pdf: Source PDF file
- output.pdf: Destination file path
- degrees: Rotation angle (90, 180, 270)
```

### References Best Practices

**Content That Belongs in References:**
- Detailed specifications
- API documentation
- Database schemas
- Step-by-step workflows
- Best practice details
- Examples and templates
- Domain knowledge

**Organization:**
- One topic per file
- Descriptive filenames
- 150-500 lines each
- Clear navigation from entry point

**Avoid Duplication:**
- Information lives in ONE place
- Entry point has summary
- Reference has detail
- Never copy-paste between them

**Large Files (>10k words):**
Include grep patterns in SKILL.md:
```markdown
Search `references/api_docs.md` for specific endpoints:
- "POST /users" - User creation
- "GET /users/:id" - User retrieval
- "PUT /users/:id" - User updates
```

### Assets Best Practices

**Content That Belongs in Assets:**
- Templates for output
- Images and icons
- Fonts and typography
- Boilerplate code
- Sample documents
- Binary resources

**Organization:**
- Group by type or purpose
- Descriptive directory names
- Include README if structure is complex

**Documentation in SKILL.md:**
```markdown
Copy `assets/frontend-template/` as starting point for new web applications.

The template includes:
- index.html - Main HTML structure
- styles.css - Base styling
- app.js - JavaScript framework setup
```

## Quality Standards

### Completeness Checklist

Before considering a skill complete:

- [ ] YAML frontmatter includes required fields (name, description)
- [ ] Description clearly states purpose and activation conditions
- [ ] All planned scripts implemented and documented
- [ ] All reference files created with clear purpose
- [ ] All assets included and referenced
- [ ] Entry point uses imperative voice throughout
- [ ] Navigation section links to all references
- [ ] No content duplication between entry and references
- [ ] Examples provided for complex workflows
- [ ] Red flags section warns about common mistakes
- [ ] Integration with other skills documented

### Progressive Disclosure Checklist

For skills using progressive disclosure:

- [ ] Progressive disclosure frontmatter added
- [ ] Entry point reduced to <200 lines (optimal: 140-160)
- [ ] 3-5 reference files created
- [ ] Each reference 150-500 lines
- [ ] Clear navigation with descriptions
- [ ] No duplicated content
- [ ] Descriptive reference filenames
- [ ] References organized by logical topics

### Validation and Testing

**Automated Validation:**
Use packaging script to validate:
```bash
scripts/package_skill.py <path/to/skill-folder>
```

Checks:
- YAML frontmatter format
- Required fields present
- File structure correct
- References exist

**Manual Testing:**
1. Use the skill on realistic tasks
2. Note any confusion or missing information
3. Iterate based on feedback
4. Repeat until smooth execution

## Common Anti-Patterns

### ❌ Anti-Pattern 1: Overly Detailed Entry Point

**Problem:** Entry point becomes monolithic reference manual

**Example:**
```markdown
# My Skill

## Step 1: Do This
[300 lines of detailed instructions]

## Step 2: Do That
[400 lines of detailed instructions]
```

**Fix:** Move details to references
```markdown
# My Skill

## Quick Start
1. First phase - See [workflow.md](./references/workflow.md) for details
2. Second phase - See [implementation.md](./references/implementation.md)
```

### ❌ Anti-Pattern 2: Unclear Activation Conditions

**Problem:** Claude doesn't know when to use the skill

**Example:**
```yaml
description: Helps with stuff
```

**Fix:** Specific activation conditions
```yaml
description: Creates database migration scripts. Use when user requests schema changes, table creation, or data migration for PostgreSQL or MySQL databases.
```

### ❌ Anti-Pattern 3: Second-Person Voice

**Problem:** Violates imperative voice requirement

**Example:**
```markdown
You should first load the reference file, then you can start implementing.
```

**Fix:** Imperative voice
```markdown
Load the reference file before implementing.
```

### ❌ Anti-Pattern 4: Duplicated Content

**Problem:** Same information in multiple places

**Example:**
```markdown
SKILL.md: "The API requires authentication via OAuth 2.0..."
references/api.md: "The API requires authentication via OAuth 2.0..."
```

**Fix:** Summary in entry, detail in reference
```markdown
SKILL.md: "API uses OAuth 2.0 - see references/api.md for details"
references/api.md: [Complete OAuth 2.0 implementation guide]
```

### ❌ Anti-Pattern 5: Missing Navigation

**Problem:** References exist but aren't mentioned in entry point

**Fix:** Explicit navigation section
```markdown
## Navigation

- **[API Reference](./references/api.md)** - Complete API documentation
- **[Examples](./references/examples.md)** - Sample implementations
```

### ❌ Anti-Pattern 6: Unused Resources

**Problem:** Example files from init script left in skill

**Fix:** Delete unused directories and files
```bash
rm -rf scripts/ references/ assets/  # If not needed
```

## Naming Conventions

### Skill Names
- kebab-case
- Descriptive and specific
- Avoid generic terms
- Examples: `pdf-editor`, `brand-guidelines`, `mcp-builder`

### Reference Filenames
- kebab-case
- Indicate content clearly
- Group related content
- Examples: `workflow.md`, `best-practices.md`, `api-reference.md`

### Script Names
- snake_case for Python
- kebab-case for Bash
- Clear purpose
- Examples: `rotate_pdf.py`, `init-skill.sh`

### Asset Names
- Descriptive
- Include type/purpose
- Examples: `logo.png`, `template.html`, `boilerplate/`

## Maintenance Best Practices

### Version Control
- Track skills in git
- Commit after each iteration
- Tag major versions
- Include changelog

### Documentation Updates
- Update as skill evolves
- Keep examples current
- Remove outdated information
- Test documented workflows

### User Feedback
- Collect usage feedback
- Track common issues
- Iterate based on patterns
- Improve clarity continuously

## Meta-Skill Considerations

For skills that teach skill creation (like this one):

**Demonstrate Your Own Teachings:**
- Apply patterns you recommend
- Use structure you advocate
- Follow guidelines you establish
- Be the example

**Reference Recent Work:**
- Cite recently optimized skills
- Show before/after examples
- Demonstrate real improvements
- Prove effectiveness

**Stay Current:**
- Update as patterns evolve
- Incorporate new best practices
- Refine based on experience
- Lead by example

**This skill-creator skill exemplifies progressive disclosure by:**
- Entry point <200 lines
- 5 well-organized references
- Clear navigation
- No content duplication
- Imperative voice throughout
- Recent examples (mcp-builder, testing-anti-patterns)
