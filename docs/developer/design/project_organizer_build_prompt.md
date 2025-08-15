# Build Instructions: Project Organizer Agent for Claude MPM

## Overview
I need you to build a **Project Organizer Agent** for Claude MPM that intelligently manages project file organization. This agent should integrate seamlessly with Claude MPM's existing agent framework, working alongside Claude's native Task tool to maintain consistent project structure.

## Agent Core Functionality

### Primary Purpose
Create an agent that:
1. **Learns** the existing organization pattern of any project by analyzing its current structure
2. **Enforces** discovered patterns when new files are created or existing files need reorganization
3. **Suggests** optimal locations for documentation, scripts, assets, and other non-code files
4. **Maintains** a Claude.MD file with links to organization guidelines and structure documentation

### Key Capabilities

#### 1. Pattern Detection & Learning
The agent should analyze the project to identify:
- **Directory structure patterns**: How folders are organized (by feature, by type, by domain)
- **Naming conventions**: camelCase, kebab-case, PascalCase, snake_case usage
- **File type locations**: Where different file types typically live (docs/, scripts/, assets/, etc.)
- **Special conventions**: Project-specific rules (e.g., all SQL in `database/`, all configs in root)

Example detection logic:
```python
# The agent should detect patterns like:
# - All markdown docs in /docs or /documentation
# - Scripts organized by purpose (/scripts/build, /scripts/deploy)
# - Assets grouped by type (/assets/images, /assets/fonts)
# - Test files colocated or in separate __tests__ directories
```

#### 2. Intelligent File Placement
When asked where a file should go, the agent should:
- Consider the file's purpose and type
- Apply learned project patterns
- Suggest the most appropriate location
- Provide reasoning based on existing conventions

Example interaction:
```
User: "Where should I put a new database migration script?"
Agent: "Based on your project structure, database migration scripts belong in `/database/migrations/`. 
       I notice you follow a pattern of:
       - SQL scripts in `/database/`
       - Migrations specifically in `/database/migrations/` with timestamp prefixes
       - Seeds in `/database/seeds/`
       
       Suggested filename: `/database/migrations/20240115_add_user_roles.sql`"
```

#### 3. Organization Enforcement
The agent should:
- Flag files that violate established patterns
- Suggest file moves to maintain consistency
- Provide batch reorganization recommendations
- Create pre-commit hooks or validation scripts

#### 4. Claude.MD Maintenance
The agent must maintain a `Claude.MD` file (or append to existing) that includes:
- **Project Structure Guidelines**: Document the discovered/enforced patterns
- **Organization Rules**: Clear rules for where different file types belong
- **Quick Reference**: A tree view or table showing the standard structure
- **Links to Documentation**: References to relevant style guides or conventions

Example Claude.MD section:
```markdown
## Project Organization Guidelines

### Directory Structure
- `/src` - Application source code (TypeScript/JavaScript)
- `/docs` - Project documentation (Markdown)
- `/scripts` - Build, deploy, and utility scripts
- `/assets` - Static assets (images, fonts, icons)
- `/config` - Configuration files
- `/tests` - Test files (if not colocated)

### File Placement Rules
1. **Documentation**: All .md files go in `/docs`, organized by topic
2. **Scripts**: Utility scripts in `/scripts`, grouped by purpose
3. **Configs**: Root level for main configs, `/config` for environment-specific
4. **Database**: SQL and migrations in `/database/migrations`
5. **Assets**: Organized by type in `/assets/{images|fonts|icons}`

### Naming Conventions
- Directories: kebab-case
- TypeScript files: PascalCase for components, camelCase for utilities
- Scripts: snake_case with descriptive names
```

## Implementation Requirements

### 1. Claude MPM Integration
The agent must:
- Extend Claude MPM's base agent class
- Register in the agent hierarchy (project-level agent)
- Support training for pattern improvement
- Work with existing hooks system

### 2. Core Commands to Implement

The agent should respond to commands by executing appropriate bash scripts that:

```bash
# Analyze project structure
analyze_structure() {
    # Scan directory tree and identify patterns
    # Output findings to .claude-mpm/project-structure.json
}

# Suggest file location
suggest_location() {
    # Parse file type and purpose
    # Apply learned patterns
    # Return suggested path
}

# Validate current structure
validate_structure() {
    # Check files against patterns
    # Report violations
}

# Generate reorganization suggestions
reorganize_suggestions() {
    # Analyze misplaced files
    # Generate move commands
}

# Update Claude.MD
update_claude_md() {
    # Generate/update organization guidelines
    # Include directory maps and rules
}
```

### 3. User Interaction Examples

```bash
# Initial setup
claude-mpm organize --analyze
> Analyzing project structure...
> Detected patterns: feature-based organization, kebab-case directories
> Created Claude.MD with organization guidelines

# File placement query
claude-mpm organize --place "new-auth-middleware.ts"
> Suggested location: /src/features/auth/middleware/new-auth-middleware.ts
> Reasoning: Auth-related files organized under features/auth/

# Validation
claude-mpm organize --validate
> Found 3 files that violate organization patterns:
> - /src/utils/auth.ts → should be in /src/features/auth/utils/
> - /login.test.js → should be in /src/features/auth/__tests__/
> - /docs/readme.md → should be /docs/README.md (uppercase convention)

# Batch reorganization
claude-mpm organize --fix --dry-run
> Proposed moves:
> - Move /src/utils/auth.ts → /src/features/auth/utils/auth.ts
> - Move /login.test.js → /src/features/auth/__tests__/login.test.js
> - Rename /docs/readme.md → /docs/README.md
```

## Special Considerations

### 1. Respect Existing .gitignore
Never suggest moving files that are gitignored (like node_modules, .env)

### 2. Framework Awareness
Recognize framework-specific conventions:
- Next.js: pages/, public/, styles/ conventions
- Django: apps structure, manage.py location
- Rails: MVC directory structure

### 3. Conflict Resolution
When patterns conflict:
- Prefer more specific patterns over general ones
- Allow user overrides via configuration
- Document exceptions in Claude.MD

### 4. Performance
- Cache structure analysis results
- Incremental updates rather than full rescans
- Efficient pattern matching algorithms

## Success Criteria

The agent is successful when it can:
1. **Accurately detect** organization patterns in 90% of projects
2. **Correctly suggest** file locations that match project conventions
3. **Maintain** an up-to-date Claude.MD with clear guidelines
4. **Adapt** to user corrections and project evolution
5. **Integrate** seamlessly with Claude MPM's existing agent system
6. **Provide** clear reasoning for all suggestions
7. **Handle** complex projects with mixed patterns gracefully

## Example Claude.MD Output

The agent should generate/update a Claude.MD section like:

```markdown
# Project Organization Guide
*Generated by Claude MPM Project Organizer Agent*
*Last updated: 2024-01-15*

## Detected Structure Pattern: Feature-Based Organization

### Core Principles
- Files grouped by feature/domain rather than technical type
- Each feature is self-contained with its own tests, styles, and utilities
- Shared code in `/src/shared` or `/src/common`

### Directory Map
```
project-root/
├── src/
│   ├── features/
│   │   ├── auth/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── services/
│   │   │   ├── utils/
│   │   │   └── __tests__/
│   │   └── dashboard/
│   │       └── [same structure]
│   ├── shared/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── utils/
│   └── config/
├── docs/
│   ├── api/
│   ├── guides/
│   └── architecture/
├── scripts/
│   ├── build/
│   ├── deploy/
│   └── utils/
└── assets/
    ├── images/
    ├── fonts/
    └── icons/
```

### File Placement Quick Reference

| File Type | Location | Example |
|-----------|----------|---------|
| React Component | `/src/features/{feature}/components/` | `UserProfile.tsx` |
| API Service | `/src/features/{feature}/services/` | `authService.ts` |
| Custom Hook | `/src/features/{feature}/hooks/` | `useAuth.ts` |
| Documentation | `/docs/{category}/` | `authentication-guide.md` |
| Build Script | `/scripts/build/` | `compile-assets.sh` |
| Database Migration | `/database/migrations/` | `001_create_users.sql` |
| Environment Config | `/config/` or root | `.env.development` |
| Static Assets | `/assets/{type}/` | `logo.svg` |

### Naming Conventions

- **Directories**: kebab-case (`user-profile`, `auth-service`)
- **Components**: PascalCase (`UserProfile.tsx`, `AuthModal.tsx`)
- **Utilities/Hooks**: camelCase (`formatDate.ts`, `useAuth.ts`)
- **Scripts**: snake_case (`build_production.sh`, `run_tests.py`)
- **Documentation**: kebab-case (`api-guide.md`, `setup-instructions.md`)

### Enforcement Rules

1. ✅ All test files must be in `__tests__` directories or colocated with `.test.ts` suffix
2. ✅ No business logic in `/src/shared` - only truly shared utilities
3. ✅ Database files must be in `/database` with proper subdirectories
4. ✅ All markdown documentation in `/docs`
5. ✅ Configuration files in `/config` or root (for tools that require root placement)

### Exceptions & Overrides

- `README.md` - Root level (standard convention)
- `package.json`, `tsconfig.json` - Root level (required by tools)
- `.github/` - Root level (GitHub requirement)
- Build outputs in `/dist` or `/build` (gitignored)

### Related Guidelines

- [TypeScript Style Guide](./docs/guides/typescript-style.md)
- [Component Architecture](./docs/architecture/components.md)
- [Testing Standards](./docs/guides/testing.md)
```

## Final Notes

This agent should feel like a knowledgeable team member who:
- Understands and respects your project's existing patterns
- Helps maintain consistency without being rigid
- Learns and adapts as the project evolves
- Provides clear, actionable guidance
- Makes organization decisions transparent and logical

Build this as a production-ready Claude MPM agent that enhances developer productivity by eliminating organization decisions and maintaining project consistency.