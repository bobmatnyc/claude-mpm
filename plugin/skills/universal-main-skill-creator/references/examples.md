# Skill Creation Examples

## Complete Skill Examples

This reference provides real-world examples of well-crafted skills demonstrating various patterns and approaches.

## Example 1: mcp-builder (Progressive Disclosure)

### Overview

**Purpose:** Build high-quality MCP servers for LLM integration

**Challenge:** Complex topic with multiple implementation languages, extensive best practices, and detailed workflows

**Solution:** Progressive disclosure with 6 reference files

### Structure

```
mcp-builder/
├── SKILL.md (160 lines)
└── references/
    ├── design_principles.md - Agent-centric design philosophy
    ├── workflow.md - 4-phase development process
    ├── mcp_best_practices.md - Universal MCP guidelines
    ├── python_mcp_server.md - Python implementation patterns
    ├── node_mcp_server.md - TypeScript implementation patterns
    └── evaluation.md - Testing and iteration
```

### Entry Point (SKILL.md)

**Frontmatter:**
```yaml
---
name: mcp-builder
description: Create high-quality MCP servers that enable LLMs to effectively interact with external services. Use when building MCP integrations for APIs or services in Python (FastMCP) or Node/TypeScript (MCP SDK).
progressive_disclosure:
  entry_point:
    summary: "Build agent-friendly MCP servers through research-driven design, thoughtful implementation, and evaluation-based iteration"
    when_to_use: "When integrating external APIs/services via MCP protocol. Prioritize agent workflows over API wrappers, optimize for context efficiency, design actionable errors."
    quick_start: "1. Research protocol & API docs 2. Plan agent-centric tools 3. Implement with validation 4. Create evaluations 5. Iterate based on agent feedback"
  references:
    - design_principles.md
    - workflow.md
    - mcp_best_practices.md
    - python_mcp_server.md
    - node_mcp_server.md
    - evaluation.md
---
```

**Key Sections:**
- **The Iron Law** - "Design for agents, not humans"
- **Core Principles** - 5 essential guidelines
- **Quick Start** - 4-phase workflow with reference links
- **Navigation** - Annotated list of all 6 references
- **Red Flags** - Warning signs to stop and reconsider

**What Makes It Effective:**
- Clear activation conditions in description
- Strong Iron Law sets philosophy
- Quick start maps to detailed workflow reference
- Navigation explains when to load each reference
- 160 lines = 23% reduction from original 209

### Reference Organization

**By Topic and Phase:**
1. **design_principles.md** - Load FIRST before implementation
2. **workflow.md** - Complete 4-phase process with decision trees
3. **mcp_best_practices.md** - Universal guidelines (language-agnostic)
4. **python_mcp_server.md** - Load during Phase 2 for Python
5. **node_mcp_server.md** - Load during Phase 2 for TypeScript
6. **evaluation.md** - Load during Phase 4

**Content Distribution:**
- Entry: Core philosophy + quick start (160 lines)
- References: Deep implementation details (~2000 lines total)
- Total: ~2160 lines (vs 209 monolithic)
- Context saved: Load only what's needed for current language/phase

## Example 2: testing-anti-patterns (Ultra-Lean Entry)

### Overview

**Purpose:** Prevent common testing mistakes

**Challenge:** Multiple distinct anti-patterns, detection guidance, and TDD connection

**Solution:** Ultra-lean 140-line entry with 4 focused references

### Structure

```
testing-anti-patterns/
├── SKILL.md (140 lines)
└── references/
    ├── core-anti-patterns.md - Patterns 1-3
    ├── completeness-anti-patterns.md - Patterns 4-5
    ├── detection-guide.md - Red flags and gates
    └── tdd-connection.md - Prevention through TDD
```

### Entry Point (SKILL.md)

**Frontmatter:**
```yaml
---
name: Testing Anti-Patterns
description: Never test mock behavior. Never add test-only methods to production classes. Understand dependencies before mocking.
when_to_use: when writing or changing tests, adding mocks, or tempted to add test-only methods to production code
progressive_disclosure:
  entry_point:
    summary: "Avoid testing mocks, test-only production methods, and incomplete mocking. Test real behavior, not mock behavior."
    when_to_use: "When writing tests, adding mocks, reviewing test failures, or tempted to add test-only methods to production code."
    quick_start: "1. Ask: 'Am I testing real behavior?' 2. Check: 'Is this method only for tests?' 3. Verify: 'Do I understand what I'm mocking?' 4. Confirm: 'Is my mock complete?' 5. Apply: TDD prevents these patterns"
  references:
    - core-anti-patterns.md
    - completeness-anti-patterns.md
    - detection-guide.md
    - tdd-connection.md
---
```

**Key Sections:**
- **The Iron Laws** - 5 non-negotiable rules
- **Core Anti-Pattern Categories** - Brief summary + link to details
- **Quick Detection Checklist** - Runnable checklist
- **The Bottom Line** - Core philosophy
- **Navigation** - 4 references with clear purposes

**What Makes It Effective:**
- Extremely focused entry point (140 lines)
- Iron Laws immediately establish boundaries
- Quick checklist provides instant value
- Entry point alone prevents most anti-patterns
- Deep dive available in references for learning

### Reference Organization

**By Anti-Pattern Category:**
1. **core-anti-patterns.md** - Patterns 1-3 (testing mocks, test-only methods, uninformed mocking)
2. **completeness-anti-patterns.md** - Patterns 4-5 (incomplete mocks, tests as afterthought)

**By Function:**
3. **detection-guide.md** - How to spot these patterns
4. **tdd-connection.md** - How TDD prevents them

**Content Distribution:**
- Entry: Iron Laws + quick checklist (140 lines)
- References: Detailed analysis + examples (~800 lines total)
- Optimal for quick reference with depth available

## Example 3: PDF Editor (Simple Skill with Scripts)

### Overview

**Purpose:** Rotate, merge, and manipulate PDF files

**Challenge:** Repetitive code for PDF operations

**Solution:** Python scripts for common operations

### Structure

```
pdf-editor/
├── SKILL.md (80 lines)
└── scripts/
    ├── rotate_pdf.py
    ├── merge_pdfs.py
    └── split_pdf.py
```

### Entry Point (SKILL.md)

```yaml
---
name: pdf-editor
description: Rotate, merge, split, and manipulate PDF files. Use when users need to perform PDF operations like rotation, combining multiple PDFs, or extracting pages.
---

# PDF Editor

## Overview

Provides scripts for common PDF operations: rotation, merging, splitting, and page extraction.

## When to Use This Skill

- User requests PDF rotation
- Multiple PDFs need combining
- PDF pages need extraction
- PDF operations need to be reliable and fast

## Available Operations

### Rotate PDF
Execute `scripts/rotate_pdf.py <input.pdf> <output.pdf> <degrees>` to rotate PDFs.

Parameters:
- input.pdf: Source PDF file
- output.pdf: Destination file path
- degrees: Rotation angle (90, 180, 270)

Example:
```
scripts/rotate_pdf.py document.pdf rotated.pdf 90
```

### Merge PDFs
Execute `scripts/merge_pdfs.py <output.pdf> <input1.pdf> <input2.pdf> ...` to combine PDFs.

### Split PDF
Execute `scripts/split_pdf.py <input.pdf> <page_number>` to split PDF at specific page.
```

**What Makes It Effective:**
- Simple 80-line skill (no progressive disclosure needed)
- Scripts eliminate repetitive code writing
- Clear usage documentation
- Focused on common operations

### Why Scripts?

**Without skill:**
- User: "Rotate this PDF 90 degrees"
- Claude: Writes PDF rotation code from scratch (50+ lines)
- Code may have bugs, needs testing
- Same code rewritten for each request

**With skill:**
- User: "Rotate this PDF 90 degrees"
- Claude: Executes `scripts/rotate_pdf.py document.pdf rotated.pdf 90`
- Pre-tested, reliable code
- Instant execution

## Example 4: Brand Guidelines (Reference + Assets)

### Overview

**Purpose:** Ensure consistent brand application

**Challenge:** Brand rules, color codes, fonts, logo files

**Solution:** Reference documentation + asset files

### Structure

```
brand-guidelines/
├── SKILL.md (90 lines)
├── references/
│   └── brand-standards.md
└── assets/
    ├── logo-primary.png
    ├── logo-white.png
    ├── logo-black.png
    ├── fonts/
    │   ├── BrandFont-Regular.ttf
    │   └── BrandFont-Bold.ttf
    └── color-palette.png
```

### Entry Point (SKILL.md)

```yaml
---
name: brand-guidelines
description: Apply company brand guidelines to documents, presentations, and marketing materials. Use when creating customer-facing content that must match brand standards.
---

# Brand Guidelines

## Overview

Ensures all customer-facing content follows company brand standards including colors, fonts, logo usage, and tone of voice.

## When to Use This Skill

- Creating presentations, documents, or marketing materials
- User mentions "brand guidelines" or "brand standards"
- Customer-facing content needs consistency
- Logo placement or usage questions

## Brand Assets

### Logos
Available in `assets/`:
- `logo-primary.png` - Full color logo (primary use)
- `logo-white.png` - White logo (dark backgrounds)
- `logo-black.png` - Black logo (print, grayscale)

### Fonts
Brand fonts in `assets/fonts/`:
- BrandFont-Regular.ttf (body text)
- BrandFont-Bold.ttf (headers)

### Color Palette
Reference `assets/color-palette.png` for official brand colors.

## Detailed Standards

Load `references/brand-standards.md` for:
- Complete color codes (HEX, RGB, CMYK)
- Logo usage rules and clearspace
- Typography hierarchy and sizing
- Tone of voice guidelines
- Do's and don'ts
```

### Reference Content (brand-standards.md)

```markdown
# Brand Standards Reference

## Color Palette

### Primary Colors
- Brand Blue: #0066CC (RGB: 0, 102, 204)
- Brand White: #FFFFFF
- Brand Black: #1A1A1A

### Secondary Colors
- Accent Orange: #FF6600
- Neutral Gray: #7F7F7F

### Usage
- Brand Blue: Primary CTA buttons, headers
- Accent Orange: Highlights, secondary CTAs
- Neutral Gray: Body text, borders

## Logo Usage

### Clearspace
Maintain minimum clearspace equal to height of "M" in logo around all sides.

### Minimum Size
- Digital: 120px width minimum
- Print: 1 inch width minimum

### Do's
- Use provided logo files
- Maintain aspect ratio
- Place on solid backgrounds

### Don'ts
- Never stretch or distort
- Never add effects or shadows
- Never change colors
- Never place on busy backgrounds

[... additional sections ...]
```

**What Makes It Effective:**
- Assets provide ready-to-use brand files
- Reference contains detailed specifications
- Entry point explains what's available
- Claude can apply standards without asking user
- Ensures brand consistency

## Example 5: Database Query Builder (References)

### Overview

**Purpose:** Write safe, efficient database queries

**Challenge:** Complex schema, multiple tables, relationships

**Solution:** Schema documentation in references

### Structure

```
database-query-builder/
├── SKILL.md (120 lines)
└── references/
    ├── schema.md - Table structures and relationships
    ├── query-patterns.md - Common query templates
    └── optimization.md - Performance best practices
```

### Entry Point (SKILL.md)

```yaml
---
name: database-query-builder
description: Write safe, efficient database queries for the company PostgreSQL database. Use when user requests data analysis, reporting, or needs to query customer, order, or product tables.
---

# Database Query Builder

## Overview

Provides schema documentation and query patterns for safe, efficient database access.

## When to Use This Skill

- User requests data from database
- Analytics or reporting queries needed
- Mentions customer, order, product, or inventory data
- Data export or analysis tasks

## Query Process

1. Load `references/schema.md` to understand table structure
2. Identify required tables and relationships
3. Review `references/query-patterns.md` for similar queries
4. Write query using best practices from `references/optimization.md`
5. Use parameterized queries (never string concatenation)

## Key Reminders

- Always use parameterized queries for safety
- Include LIMIT clauses for exploratory queries
- Join tables efficiently (use indexes)
- Test queries on small data sets first

## Navigation

- **[Schema Reference](./references/schema.md)** - Complete table structures, columns, relationships, indexes
- **[Query Patterns](./references/query-patterns.md)** - Common query templates and examples
- **[Optimization Guide](./references/optimization.md)** - Performance best practices and anti-patterns
```

### Reference Content (schema.md)

```markdown
# Database Schema Reference

## Customers Table

```sql
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_customers_email ON customers(email);
```

**Columns:**
- `id` - Primary key, auto-increment
- `email` - Unique customer email
- `name` - Customer full name
- `created_at` - Account creation timestamp
- `updated_at` - Last update timestamp

**Relationships:**
- `orders.customer_id` → `customers.id` (one-to-many)

## Orders Table

[... additional tables ...]

## Common Queries

Search for specific queries in this file:
- "customer email lookup" - Find customer by email
- "order history" - Get customer's order history
- "revenue by month" - Monthly revenue aggregation
```

**What Makes It Effective:**
- Schema reference keeps detailed table structures
- Claude loads schema before writing queries
- Prevents SQL injection via parameterization requirement
- Query patterns provide starting points
- Grep search patterns for large schema files

## Example 6: Frontend Webapp Builder (Assets)

### Overview

**Purpose:** Build web applications quickly

**Challenge:** Same boilerplate code for each app

**Solution:** Template assets with boilerplate code

### Structure

```
frontend-webapp-builder/
├── SKILL.md (100 lines)
└── assets/
    ├── vanilla-template/
    │   ├── index.html
    │   ├── styles.css
    │   └── app.js
    └── react-template/
        ├── package.json
        ├── public/
        └── src/
            ├── App.jsx
            ├── index.jsx
            └── styles.css
```

### Entry Point (SKILL.md)

```yaml
---
name: frontend-webapp-builder
description: Build frontend web applications using vanilla JavaScript or React. Use when user requests a web app, dashboard, or interactive webpage.
---

# Frontend Webapp Builder

## Overview

Provides boilerplate templates for rapid web application development.

## When to Use This Skill

- User requests a web app or dashboard
- Interactive webpage needed
- Frontend prototype required
- Quick demo or proof-of-concept

## Available Templates

### Vanilla JavaScript Template
Copy `assets/vanilla-template/` for simple, dependency-free apps.

Includes:
- `index.html` - Semantic HTML5 structure
- `styles.css` - Modern CSS with CSS Grid and Flexbox
- `app.js` - Clean JavaScript with module pattern

Best for: Simple apps, quick demos, no build step needed

### React Template
Copy `assets/react-template/` for complex, stateful applications.

Includes:
- Full React setup with hooks
- Component structure
- Modern build configuration
- Development server ready

Best for: Complex state management, reusable components, larger apps

## Development Workflow

1. Copy appropriate template
2. Customize HTML/JSX structure
3. Add application-specific logic
4. Style with CSS/styled-components
5. Test in browser
```

**What Makes It Effective:**
- Asset templates eliminate boilerplate writing
- Two options for different complexity levels
- Ready-to-run code
- Claude customizes rather than creates from scratch
- Faster development, fewer errors

## Pattern Summary

### When to Use Each Approach

**Scripts:**
- Repetitive code operations
- Need deterministic execution
- Complex algorithms
- Example: PDF operations, file conversions

**References:**
- Detailed specifications
- Domain knowledge
- Multi-step workflows
- Example: API docs, database schemas, processes

**Assets:**
- Templates and boilerplate
- Binary files (images, fonts)
- Starting point code
- Example: Project templates, brand resources

**Progressive Disclosure:**
- Skill >150 lines
- Multiple distinct topics
- Complex workflows
- Example: Technical guides, multi-phase processes

### Structure Selection Guide

**Simple Skill (<150 lines):**
- Single SKILL.md
- Maybe scripts or assets
- No progressive disclosure needed

**Medium Skill (150-300 lines):**
- SKILL.md entry point (150-160 lines)
- 2-3 reference files
- Progressive disclosure recommended

**Complex Skill (300+ lines if monolithic):**
- SKILL.md entry point (140-160 lines)
- 4-6 reference files
- Progressive disclosure required

## Key Takeaways

1. **Match structure to content** - Use references for documentation, scripts for code, assets for templates
2. **Apply progressive disclosure** - Keep entry point lean, move details to references
3. **Demonstrate your teachings** - Meta-skills should exemplify their patterns
4. **Reference recent work** - Show real examples of successful skills
5. **Organize logically** - Group by topic, phase, or function
6. **Document clearly** - Explain when to load each resource
7. **Avoid duplication** - Information lives in one place
8. **Test with real tasks** - Ensure skill actually helps Claude
