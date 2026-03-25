# Skill Structure and Anatomy

## Complete Skill Architecture

Every skill consists of a required SKILL.md file and optional bundled resources:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/          - Executable code (Python/Bash/etc.)
    ├── references/       - Documentation intended to be loaded into context as needed
    └── assets/           - Files used in output (templates, icons, fonts, etc.)
```

## SKILL.md Requirements

### YAML Frontmatter (required)

The frontmatter metadata determines when Claude will activate and use the skill.

**Required Fields:**
- `name:` - Skill identifier (kebab-case)
- `description:` - Clear explanation of purpose and activation conditions

**Metadata Quality Guidelines:**
- Be specific about what the skill does and when to use it
- Use third-person voice (e.g., "This skill should be used when..." instead of "Use this skill when...")
- Include activation conditions in the description
- Mention key capabilities and constraints

**Example:**
```yaml
---
name: skill-creator
description: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.
license: Complete terms in LICENSE.txt
---
```

### Progressive Disclosure Frontmatter (recommended for skills >150 lines)

For skills using the progressive disclosure pattern, add structured metadata to guide Claude:

```yaml
progressive_disclosure:
  entry_point:
    summary: "One-line description of core workflow"
    when_to_use: "Specific activation conditions and priorities"
    quick_start: "5-step workflow overview"
  references:
    - reference-file-1.md
    - reference-file-2.md
```

**Example from mcp-builder:**
```yaml
progressive_disclosure:
  entry_point:
    summary: "Build agent-friendly MCP servers through research-driven design, thoughtful implementation, and evaluation-based iteration"
    when_to_use: "When integrating external APIs/services via MCP protocol. Prioritize agent workflows over API wrappers, optimize for context efficiency, design actionable errors."
    quick_start: "1. Research protocol & API docs 2. Plan agent-centric tools 3. Implement with validation 4. Create evaluations 5. Iterate based on agent feedback"
  references:
    - design_principles.md
    - workflow.md
    - mcp_best_practices.md
```

### Markdown Body Content

**Writing Style:**
- Use **imperative/infinitive form** (verb-first instructions), not second person
- Write objective, instructional language
- Example: "To accomplish X, do Y" (not "You should do X")
- Maintain consistency and clarity for AI consumption

**Recommended Sections for Entry Point:**
1. **Overview** - What the skill provides (2-3 sentences)
2. **When to Use This Skill** - Clear activation conditions
3. **The Iron Law** - Non-negotiable principles (if applicable)
4. **Core Principles** - Foundational guidelines (brief)
5. **Quick Start** - High-level workflow
6. **Navigation** - Links to detailed reference files
7. **Key Reminders** - Critical points to remember
8. **Red Flags** - Warning signs to stop and reconsider
9. **Integration with Other Skills** - Related skills
10. **Real-World Impact** - Evidence of effectiveness (if applicable)

## Bundled Resources

### Scripts Directory (`scripts/`)

**Purpose:** Executable code for tasks requiring deterministic reliability or repeatedly rewritten logic.

**When to include:**
- Same code is repeatedly rewritten
- Deterministic reliability is essential
- Complex operations benefit from pre-tested implementation

**Examples:**
- `scripts/rotate_pdf.py` - PDF rotation tasks
- `scripts/init_skill.py` - Skill initialization
- `scripts/package_skill.py` - Skill packaging and validation

**Benefits:**
- Token efficient (can be executed without reading into context)
- Deterministic execution
- Testable and versioned

**Note:** Scripts may still need to be read by Claude for patching or environment-specific adjustments.

### References Directory (`references/`)

**Purpose:** Documentation and reference material loaded into context as needed to inform Claude's process.

**When to include:**
- Documentation Claude should reference while working
- Detailed specifications too lengthy for entry point
- Domain knowledge that varies by project
- Complex workflows requiring step-by-step guidance

**Examples:**
- `references/finance.md` - Financial schemas
- `references/mnda.md` - Company NDA template
- `references/policies.md` - Company policies
- `references/api_docs.md` - API specifications
- `references/workflow.md` - Detailed process steps
- `references/best_practices.md` - Domain-specific guidelines

**Use Cases:**
- Database schemas
- API documentation
- Domain knowledge
- Company policies
- Detailed workflow guides
- Technical specifications
- Design principles

**Benefits:**
- Keeps SKILL.md lean and focused
- Loaded only when Claude determines it's needed
- Scales to unlimited detail without bloating entry point
- Organizes information by topic

**Best Practices:**
- If files are large (>10k words), include grep search patterns in SKILL.md
- Avoid duplication between SKILL.md and references
- Information should live in ONE place (prefer references for detailed content)
- Keep only essential procedural instructions in SKILL.md
- Move detailed reference material, schemas, and examples to reference files
- Use descriptive filenames that indicate content

**Progressive Disclosure Pattern:**
Structure references to answer specific questions:
- Core concepts and principles
- Step-by-step workflows
- Technical implementation details
- Examples and templates
- Advanced patterns and edge cases

### Assets Directory (`assets/`)

**Purpose:** Files not intended for context loading, but used in the output Claude produces.

**When to include:**
- Files needed in final deliverables
- Templates that get copied or modified
- Binary resources (images, fonts, etc.)
- Boilerplate code structures

**Examples:**
- `assets/logo.png` - Brand assets
- `assets/slides.pptx` - PowerPoint templates
- `assets/frontend-template/` - HTML/React boilerplate
- `assets/font.ttf` - Typography resources
- `assets/contract-template.docx` - Document templates

**Use Cases:**
- Templates
- Images and icons
- Boilerplate code
- Fonts and typography
- Sample documents
- Frontend frameworks

**Benefits:**
- Separates output resources from documentation
- Enables Claude to use files without loading into context
- Provides ready-to-use starting points
- Maintains consistency across outputs

## Progressive Disclosure Design Principle

Skills use a three-level loading system to manage context efficiently:

1. **Metadata (name + description)** - Always in context (~100 words)
   - Determines skill activation
   - Appears in skill catalog
   - Should clearly indicate purpose and usage

2. **SKILL.md body** - When skill triggers (<5k words, optimal: 1-2k words)
   - Core workflow and principles
   - Quick start guide
   - Navigation to deeper resources
   - Essential reminders and warnings

3. **Bundled resources** - As needed by Claude (Unlimited*)
   - Detailed specifications
   - Complete workflows
   - Examples and templates
   - Technical implementation guides

*Unlimited because scripts can be executed without reading into context window.

**Benefits:**
- Efficient context management
- Progressive depth based on need
- Scales from simple to complex tasks
- Reduces cognitive load on entry
- Enables specialization without bloat

**Application Guidelines:**
- Entry point <200 lines (optimal: 140-160 lines)
- Each reference file 150-500 lines
- Clear navigation from entry to references
- Self-documenting file names
- Avoid content duplication
