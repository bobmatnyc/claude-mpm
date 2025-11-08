# Skill Creation Workflow

## Complete Six-Step Process

Follow this workflow in order, skipping steps only when there is a clear reason they are not applicable.

## Step 1: Understanding the Skill with Concrete Examples

**When to skip:** Only when the skill's usage patterns are already clearly understood.

**Purpose:** Create effective skills by understanding concrete examples of how the skill will be used.

### Approach

Understanding can come from:
1. **Direct user examples** - User provides real scenarios
2. **Generated examples** - Create scenarios validated with user feedback

### Discovery Questions

Ask targeted questions to understand the skill's scope and usage:

**For an image-editor skill example:**
- "What functionality should the image-editor skill support? Editing, rotating, anything else?"
- "Can you give some examples of how this skill would be used?"
- "I can imagine users asking for things like 'Remove the red-eye from this image' or 'Rotate this image'. Are there other ways you imagine this skill being used?"
- "What would a user say that should trigger this skill?"

**General discovery questions:**
- What tasks will this skill help accomplish?
- Can you provide 3-5 realistic examples of skill usage?
- What keywords or phrases should activate this skill?
- What are the expected inputs and outputs?
- What domain knowledge is required?
- What constraints or limitations exist?

### Best Practices

- **Avoid overwhelming users** - Don't ask too many questions in a single message
- **Start with critical questions** - Ask the most important questions first
- **Follow up strategically** - Add detail questions based on initial answers
- **Validate understanding** - Summarize back to confirm comprehension
- **Collect edge cases** - Ask about unusual or complex scenarios

### Completion Criteria

Conclude this step when you have:
- Clear sense of functionality the skill should support
- 3-5 concrete usage examples
- Understanding of activation conditions
- Knowledge of expected inputs/outputs
- Awareness of edge cases and constraints

## Step 2: Planning the Reusable Skill Contents

**Purpose:** Transform concrete examples into practical skill components.

### Analysis Process

For each concrete example, analyze by:

1. **Consider execution from scratch** - How would Claude accomplish this without the skill?
2. **Identify reusable components** - What scripts, references, and assets would make repeated execution easier?
3. **Determine component types** - Classify as script, reference, or asset

### Example Analyses

**Example 1: PDF Editor Skill**

Query: "Help me rotate this PDF"

Analysis:
1. Rotating a PDF requires re-writing the same code each time
2. A `scripts/rotate_pdf.py` script would eliminate repeated code writing
3. **Component:** Script

**Example 2: Frontend Webapp Builder Skill**

Queries: "Build me a todo app", "Build me a dashboard to track my steps"

Analysis:
1. Writing a frontend webapp requires the same boilerplate HTML/React each time
2. An `assets/hello-world/` template containing boilerplate project files would provide a starting point
3. **Component:** Asset (template)

**Example 3: BigQuery Skill**

Query: "How many users have logged in today?"

Analysis:
1. Querying BigQuery requires re-discovering table schemas and relationships each time
2. A `references/schema.md` file documenting table schemas would provide persistent knowledge
3. **Component:** Reference

**Example 4: Brand Guidelines Skill**

Query: "Create a presentation following our brand guidelines"

Analysis:
1. Brand guidelines include colors, fonts, logo usage rules
2. Components needed:
   - `references/brand-guidelines.md` - Style rules and usage
   - `assets/logo.png` - Logo file for use in outputs
   - `assets/fonts/` - Brand fonts
3. **Components:** Reference + Assets

### Component Classification

**Create a Script when:**
- Same code is repeatedly rewritten
- Deterministic execution is critical
- Complex algorithm needs testing
- Performance optimization matters
- External tools need consistent invocation

**Create a Reference when:**
- Domain knowledge varies by project
- Specifications are detailed/complex
- Workflows have many steps
- API documentation is needed
- Schemas or data structures must be referenced
- Policies or guidelines exist

**Create an Asset when:**
- Templates accelerate creation
- Binary files are needed (images, fonts)
- Boilerplate code structures exist
- Starting points reduce repetition
- Consistent styling/branding required

### Deliverable

Create a structured list of reusable resources:

```
Scripts:
- scripts/rotate_pdf.py - Rotate PDF files
- scripts/optimize_image.py - Compress and optimize images

References:
- references/schema.md - Database table schemas
- references/api_docs.md - API endpoint specifications
- references/workflow.md - Detailed process steps

Assets:
- assets/template.html - Boilerplate HTML structure
- assets/logo.png - Company logo
- assets/fonts/ - Brand typography
```

## Step 3: Initializing the Skill

**When to skip:** Skill already exists and needs iteration or packaging only.

**Purpose:** Generate proper skill directory structure with templates.

### Using init_skill.py

Always use the initialization script for new skills:

```bash
scripts/init_skill.py <skill-name> --path <output-directory>
```

**Example:**
```bash
scripts/init_skill.py pdf-editor --path ./custom-skills/
```

### What the Script Creates

The initialization script:
- Creates skill directory at specified path
- Generates SKILL.md template with proper frontmatter
- Includes TODO placeholders for customization
- Creates example resource directories: `scripts/`, `references/`, `assets/`
- Adds example files demonstrating structure

### Generated Structure

```
skill-name/
├── SKILL.md                           # Template with TODOs
├── scripts/
│   └── example_script.py             # Example script (customize or delete)
├── references/
│   └── example_reference.md          # Example reference (customize or delete)
└── assets/
    └── example_asset.txt             # Example asset (customize or delete)
```

### Next Steps

After initialization:
1. Review generated SKILL.md template
2. Customize or delete example files
3. Begin implementing planned components (Step 4)

## Step 4: Edit the Skill

**Purpose:** Implement the skill for another Claude instance to use.

**Mindset:** Focus on information beneficial and non-obvious to Claude. Include procedural knowledge, domain-specific details, and reusable assets.

### Phase A: Implement Reusable Resources First

Start with the resources identified in Step 2 (scripts, references, assets).

#### Implementation Order

1. **Scripts** - Implement executable code first
2. **References** - Create documentation files
3. **Assets** - Add templates and resources

#### User Input Considerations

Some resources may require user input:
- **Brand guidelines skill** - User provides brand assets, documentation
- **Database skill** - User provides schemas, connection details
- **API integration skill** - User provides API documentation, credentials format

Ask for needed materials before implementation.

#### Clean Up Examples

Delete example files and directories not needed:
- The init script creates example files to demonstrate structure
- Most skills won't need all of `scripts/`, `references/`, and `assets/`
- Remove unused directories to keep skill clean

### Phase B: Update SKILL.md

#### Writing Style Requirements

**MANDATORY:** Use imperative/infinitive form (verb-first instructions), not second person.

✅ **Correct:**
- "To accomplish X, do Y"
- "Follow these steps to complete the task"
- "Load the reference file when needed"

❌ **Incorrect:**
- "You should do X"
- "If you need to do X"
- "You can find this in..."

**Rationale:** Maintains consistency and clarity for AI consumption.

#### Progressive Disclosure Structure

For skills expected to exceed 150 lines, implement progressive disclosure:

**Entry Point Content (SKILL.md):**
- Overview (2-3 sentences)
- When to Use This Skill
- The Iron Law (if applicable)
- Core Principles (brief)
- Quick Start (workflow summary)
- Navigation (links to references)
- Key Reminders
- Red Flags - STOP
- Integration with Other Skills
- Real-World Impact (if applicable)

**Target:** 140-160 lines for entry point

**Reference Content:**
- Detailed specifications
- Step-by-step workflows
- Technical implementation guides
- Examples and templates
- Best practices
- Advanced patterns

**Target:** 150-500 lines per reference file, 3-5 files

#### Core Questions to Answer

Complete SKILL.md by answering:

1. **What is the purpose of the skill, in a few sentences?**
   - Clear, concise overview
   - Key capabilities
   - Primary use cases

2. **When should the skill be used?**
   - Specific activation conditions
   - Keywords or scenarios that trigger skill
   - When NOT to use the skill

3. **In practice, how should Claude use the skill?**
   - Reference all scripts, references, and assets
   - Explain when to load each resource
   - Provide workflow guidance
   - Include navigation to detailed content

#### Reference Integration

Ensure SKILL.md references all reusable resources:

**Scripts:**
```markdown
Execute `scripts/rotate_pdf.py <input.pdf> <output.pdf> <degrees>` to rotate PDFs.
```

**References:**
```markdown
Load `references/schema.md` to understand database structure before writing queries.
```

**Assets:**
```markdown
Copy `assets/frontend-template/` as starting point for new web applications.
```

#### Quality Checklist

- [ ] Imperative form throughout
- [ ] All resources referenced with usage instructions
- [ ] Clear activation conditions
- [ ] Navigation to detailed references
- [ ] No duplicated content between entry and references
- [ ] Progressive disclosure frontmatter (if applicable)
- [ ] Entry point <200 lines (optimal: 140-160)

## Step 5: Packaging a Skill

**Purpose:** Validate and create distributable zip file for sharing.

### Packaging Command

```bash
scripts/package_skill.py <path/to/skill-folder>
```

**Optional output directory:**
```bash
scripts/package_skill.py <path/to/skill-folder> ./dist
```

### Automatic Validation

The packaging script automatically validates before packaging:

**Validation Checks:**
- YAML frontmatter format and required fields
- Skill naming conventions and directory structure
- Description completeness and quality
- File organization and resource references
- Progressive disclosure metadata (if present)

### Packaging Process

If validation passes, the script:
1. Creates zip file named after the skill (e.g., `my-skill.zip`)
2. Includes all files from skill directory
3. Maintains proper directory structure
4. Prepares for distribution

### Handling Validation Errors

If validation fails:
1. Script reports specific errors
2. Exits without creating package
3. Fix reported errors
4. Run packaging command again

**Common validation issues:**
- Missing required frontmatter fields
- Invalid YAML syntax
- Poor description quality
- Incorrect directory structure
- Referenced files don't exist

### Distribution

After successful packaging:
- Share the `.zip` file with users
- Users can install via Claude MPM
- Skill becomes available in their Claude instance

## Step 6: Iterate

**Purpose:** Refine skill based on real-world usage and feedback.

### When Iteration Happens

Most often immediately after using the skill:
- Fresh context of how the skill performed
- Specific examples of struggles or inefficiencies
- Clear understanding of what needs improvement

### Iteration Workflow

1. **Use the skill on real tasks**
   - Apply to actual work scenarios
   - Note difficulties and inefficiencies
   - Observe where Claude struggles

2. **Notice struggles or inefficiencies**
   - Unclear instructions
   - Missing information
   - Awkward workflows
   - Insufficient examples
   - Missing resources

3. **Identify how to update skill**
   - What SKILL.md sections need clarification?
   - What references should be added or expanded?
   - What scripts would eliminate repeated work?
   - What assets would accelerate tasks?

4. **Implement changes**
   - Update SKILL.md
   - Add/modify references
   - Create new scripts or assets
   - Improve navigation

5. **Test again**
   - Use on similar tasks
   - Verify improvements
   - Continue iterating

### Common Iteration Patterns

**Add Missing Context:**
- Skill assumes knowledge user doesn't have
- Add reference file with background information

**Clarify Workflow:**
- Steps are ambiguous or incomplete
- Expand Quick Start or create detailed workflow reference

**Automate Repetition:**
- Same code written multiple times
- Create script for repeated operations

**Provide Templates:**
- Starting from scratch repeatedly
- Add asset templates

**Improve Navigation:**
- Can't find relevant information
- Better organize references
- Add clearer signposting

### Iteration Best Practices

- **Iterate quickly** - Don't wait for perfect; improve incrementally
- **Test with real tasks** - Synthetic examples miss real-world complexity
- **Get user feedback** - They reveal blindspots
- **Track patterns** - Multiple similar struggles indicate structural issues
- **Balance detail** - More isn't always better; clarity matters

### When to Stop Iterating

A skill is mature when:
- Consistently accomplishes intended tasks
- No repeated struggles or inefficiencies
- Clear activation and usage patterns
- Well-organized and navigable
- Positive user feedback

**Remember:** Skills are living documents. Return to iterate as needs evolve.
