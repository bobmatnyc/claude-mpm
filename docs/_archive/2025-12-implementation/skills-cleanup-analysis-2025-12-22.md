# Claude MPM Skills System Analysis

**Date**: 2025-12-22
**Analysis Type**: Skills system investigation and cleanup recommendations
**Status**: Complete

## Executive Summary

Investigated the Claude MPM skills system to identify storage locations, management practices, and alignment between skills and agent types. Found 79 user-level skills and 91 project-level skills, with significant misalignment between installed skills and actual agent capabilities.

## Skills Storage Locations

### User-Level Skills
**Path**: `~/.claude/skills/`
**Count**: 79 skills
**Scope**: Global, affects all projects
**Recommendation**: Remove ALL user-level skills

### Project-Level Skills
**Path**: `/Users/masa/Projects/claude-mpm/.claude/skills/`
**Count**: 91 skills
**Scope**: Project-specific
**Recommendation**: Remove misaligned skills (see analysis below)

## Claude MPM Agent Types

Based on `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/agents_metadata.py`, the project defines these agent types:

### Core Agents
1. **documentation_agent** - Documentation and changelog generation
2. **version_control_agent** - Git operations and versioning
3. **qa_agent** - General testing and quality validation
4. **api_qa_agent** - REST/GraphQL API testing
5. **web_qa_agent** - Browser automation and E2E testing
6. **research_agent** - Technology research and analysis
7. **ops_agent** - Deployment and infrastructure
8. **security_agent** - Security auditing and vulnerability scanning
9. **engineer_agent** - Code implementation and feature development
10. **data_engineer_agent** - Data pipelines and AI API integration

### Specialized Agents
11. **project_organizer_agent** - File organization and pattern detection
12. **imagemagick_agent** - Image optimization
13. **agentic_coder_optimizer_agent** - Project optimization
14. **agent_manager** - Agent lifecycle management

## Skills Alignment Analysis

### ✅ Aligned Skills (Keep)

These skills align with agent capabilities and should be retained:

**Python Stack (data_engineer_agent, engineer_agent)**
- `toolchains-python-frameworks-flask`
- `toolchains-python-frameworks-django`
- `toolchains-python-testing-pytest`
- `toolchains-python-async-asyncio`
- `toolchains-python-async-celery`
- `toolchains-python-data-sqlalchemy`
- `toolchains-python-validation-pydantic`
- `toolchains-python-tooling-mypy`
- `toolchains-python-tooling-pyright`

**AI/ML Stack (data_engineer_agent)**
- `toolchains-ai-frameworks-langchain`
- `toolchains-ai-frameworks-langgraph`
- `toolchains-ai-frameworks-dspy`
- `toolchains-ai-protocols-mcp`
- `toolchains-ai-sdks-anthropic`

**Testing/QA (qa_agent, api_qa_agent, web_qa_agent)**
- `toolchains-javascript-testing-playwright`
- `universal-testing-webapp-testing`
- `universal-testing-test-quality-inspector`
- `universal-testing-testing-anti-patterns`
- `universal-testing-condition-based-waiting`

**Debugging (research_agent, engineer_agent)**
- `universal-debugging-systematic-debugging`
- `universal-debugging-root-cause-tracing`
- `universal-debugging-verification-before-completion`

**Ops/Infrastructure (ops_agent)**
- `toolchains-universal-infrastructure-docker`
- `toolchains-platforms-deployment-netlify`
- `toolchains-platforms-deployment-vercel`
- `toolchains-universal-emergency-release`
- `toolchains-universal-dependency-audit`

**Documentation (documentation_agent)**
- `universal-main-artifacts-builder`
- `universal-main-skill-creator`
- `universal-main-mcp-builder`

**Security (security_agent)**
- `toolchains-universal-security-api-review`
- `toolchains-universal-pr-quality`

**Collaboration (PM/coordination)**
- `universal-collaboration-brainstorming`
- `universal-collaboration-dispatching-parallel-agents`
- `universal-collaboration-requesting-code-review`
- `universal-collaboration-writing-plans`

### ❌ Misaligned Skills (Remove)

These skills target technologies NOT used by Claude MPM and should be removed:

**JavaScript/TypeScript Stack** (Claude MPM is Python-based)
- `toolchains-javascript-frameworks-nextjs` ❌
- `toolchains-javascript-frameworks-react` ❌
- `toolchains-javascript-frameworks-react-state-machine` ❌
- `toolchains-javascript-frameworks-svelte` ❌
- `toolchains-javascript-frameworks-svelte5-runes-static` ❌
- `toolchains-javascript-frameworks-sveltekit` ❌
- `toolchains-javascript-frameworks-vue` ❌
- `toolchains-javascript-frameworks-express-local-dev` ❌
- `toolchains-javascript-build-vite` ❌
- `toolchains-javascript-tooling-biome` ❌
- `toolchains-nextjs-core` ❌
- `toolchains-nextjs-v16` ❌

**TypeScript Stack** (Not applicable to Python project)
- `toolchains-typescript-core` ❌
- `toolchains-typescript-api-trpc` ❌
- `toolchains-typescript-build-turborepo` ❌
- `toolchains-typescript-data-drizzle` ❌
- `toolchains-typescript-data-kysely` ❌
- `toolchains-typescript-data-prisma` ❌
- `toolchains-typescript-frameworks-nodejs-backend` ❌
- `toolchains-typescript-state-tanstack-query` ❌
- `toolchains-typescript-state-zustand` ❌
- `toolchains-typescript-testing-jest` ❌
- `toolchains-typescript-testing-vitest` ❌
- `toolchains-typescript-validation-zod` ❌

**PHP/WordPress Stack** (Not applicable)
- `toolchains-php-frameworks-espocrm` ❌
- `toolchains-php-frameworks-wordpress-advanced-architecture` ❌
- `toolchains-php-frameworks-wordpress-block-editor` ❌
- `toolchains-php-frameworks-wordpress-plugin-fundamentals` ❌
- `toolchains-php-frameworks-wordpress-security-validation` ❌
- `toolchains-php-frameworks-wordpress-testing-qa` ❌

**Elixir Stack** (Not applicable)
- `toolchains-elixir-data-ecto-patterns` ❌
- `toolchains-elixir-frameworks-phoenix-api-channels` ❌
- `toolchains-elixir-frameworks-phoenix-liveview` ❌

**Golang Stack** (Not applicable)
- `toolchains-golang-cli` ❌
- `toolchains-golang-data` ❌
- `toolchains-golang-observability` ❌
- `toolchains-golang-testing` ❌
- `toolchains-golang-web` ❌

**Rust Stack** (Not applicable)
- `toolchains-rust-desktop-applications` ❌
- `toolchains-rust-frameworks-tauri` ❌

**UI/Frontend Stack** (Backend project, no frontend)
- `toolchains-ui-components-daisyui` ❌
- `toolchains-ui-components-headlessui` ❌
- `toolchains-ui-components-shadcn` ❌
- `toolchains-ui-styling-tailwind` ❌

**Backend Platforms** (Not currently used)
- `toolchains-platforms-backend-supabase` ❌
- `toolchains-platforms-database-neon` ❌

**AI Services** (Redundant, using Anthropic SDK directly)
- `toolchains-ai-services-openrouter` ❌
- `toolchains-ai-techniques-session-compression` ❌

**GraphQL** (Not using GraphQL)
- `toolchains-universal-data-graphql` ❌

**Example Skills** (Educational only)
- `examples-bad-interdependent-skill` ❌
- `examples-good-self-contained-skill` ❌

**Miscellaneous** (Not applicable to Claude MPM)
- `universal-main-internal-comms` ❌ (no internal comms use case)
- `universal-architecture-software-patterns` ❌ (too generic, not needed)
- `universal-infrastructure-env-manager` ❌ (redundant with ops_agent capabilities)

## Skills Cleanup Commands

### Remove ALL User-Level Skills

```bash
# Backup first (optional)
mv ~/.claude/skills ~/.claude/skills.backup-2025-12-22

# Or delete directly
rm -rf ~/.claude/skills
```

### Remove Misaligned Project-Level Skills

```bash
cd /Users/masa/Projects/claude-mpm/.claude/skills

# Remove JavaScript/TypeScript stack (12 skills)
rm -rf toolchains-javascript-frameworks-nextjs
rm -rf toolchains-javascript-frameworks-react
rm -rf toolchains-javascript-frameworks-react-state-machine
rm -rf toolchains-javascript-frameworks-svelte
rm -rf toolchains-javascript-frameworks-svelte5-runes-static
rm -rf toolchains-javascript-frameworks-sveltekit
rm -rf toolchains-javascript-frameworks-vue
rm -rf toolchains-javascript-frameworks-express-local-dev
rm -rf toolchains-javascript-build-vite
rm -rf toolchains-javascript-tooling-biome
rm -rf toolchains-nextjs-core
rm -rf toolchains-nextjs-v16

# Remove TypeScript stack (12 skills)
rm -rf toolchains-typescript-core
rm -rf toolchains-typescript-api-trpc
rm -rf toolchains-typescript-build-turborepo
rm -rf toolchains-typescript-data-drizzle
rm -rf toolchains-typescript-data-kysely
rm -rf toolchains-typescript-data-prisma
rm -rf toolchains-typescript-frameworks-nodejs-backend
rm -rf toolchains-typescript-state-tanstack-query
rm -rf toolchains-typescript-state-zustand
rm -rf toolchains-typescript-testing-jest
rm -rf toolchains-typescript-testing-vitest
rm -rf toolchains-typescript-validation-zod

# Remove PHP/WordPress stack (6 skills)
rm -rf toolchains-php-frameworks-espocrm
rm -rf toolchains-php-frameworks-wordpress-advanced-architecture
rm -rf toolchains-php-frameworks-wordpress-block-editor
rm -rf toolchains-php-frameworks-wordpress-plugin-fundamentals
rm -rf toolchains-php-frameworks-wordpress-security-validation
rm -rf toolchains-php-frameworks-wordpress-testing-qa

# Remove Elixir stack (3 skills)
rm -rf toolchains-elixir-data-ecto-patterns
rm -rf toolchains-elixir-frameworks-phoenix-api-channels
rm -rf toolchains-elixir-frameworks-phoenix-liveview

# Remove Golang stack (5 skills)
rm -rf toolchains-golang-cli
rm -rf toolchains-golang-data
rm -rf toolchains-golang-observability
rm -rf toolchains-golang-testing
rm -rf toolchains-golang-web

# Remove Rust stack (2 skills)
rm -rf toolchains-rust-desktop-applications
rm -rf toolchains-rust-frameworks-tauri

# Remove UI/Frontend stack (4 skills)
rm -rf toolchains-ui-components-daisyui
rm -rf toolchains-ui-components-headlessui
rm -rf toolchains-ui-components-shadcn
rm -rf toolchains-ui-styling-tailwind

# Remove unused platform skills (2 skills)
rm -rf toolchains-platforms-backend-supabase
rm -rf toolchains-platforms-database-neon

# Remove redundant AI services (2 skills)
rm -rf toolchains-ai-services-openrouter
rm -rf toolchains-ai-techniques-session-compression

# Remove GraphQL (1 skill)
rm -rf toolchains-universal-data-graphql

# Remove example skills (2 skills)
rm -rf examples-bad-interdependent-skill
rm -rf examples-good-self-contained-skill

# Remove miscellaneous (3 skills)
rm -rf universal-main-internal-comms
rm -rf universal-architecture-software-patterns
rm -rf universal-infrastructure-env-manager
```

### Consolidated Cleanup Script

```bash
#!/bin/bash
# Skills cleanup script for Claude MPM

SKILLS_DIR="/Users/masa/Projects/claude-mpm/.claude/skills"

cd "$SKILLS_DIR"

# Array of skills to remove
REMOVE_SKILLS=(
  # JavaScript/TypeScript
  "toolchains-javascript-frameworks-nextjs"
  "toolchains-javascript-frameworks-react"
  "toolchains-javascript-frameworks-react-state-machine"
  "toolchains-javascript-frameworks-svelte"
  "toolchains-javascript-frameworks-svelte5-runes-static"
  "toolchains-javascript-frameworks-sveltekit"
  "toolchains-javascript-frameworks-vue"
  "toolchains-javascript-frameworks-express-local-dev"
  "toolchains-javascript-build-vite"
  "toolchains-javascript-tooling-biome"
  "toolchains-nextjs-core"
  "toolchains-nextjs-v16"
  "toolchains-typescript-core"
  "toolchains-typescript-api-trpc"
  "toolchains-typescript-build-turborepo"
  "toolchains-typescript-data-drizzle"
  "toolchains-typescript-data-kysely"
  "toolchains-typescript-data-prisma"
  "toolchains-typescript-frameworks-nodejs-backend"
  "toolchains-typescript-state-tanstack-query"
  "toolchains-typescript-state-zustand"
  "toolchains-typescript-testing-jest"
  "toolchains-typescript-testing-vitest"
  "toolchains-typescript-validation-zod"
  # PHP/WordPress
  "toolchains-php-frameworks-espocrm"
  "toolchains-php-frameworks-wordpress-advanced-architecture"
  "toolchains-php-frameworks-wordpress-block-editor"
  "toolchains-php-frameworks-wordpress-plugin-fundamentals"
  "toolchains-php-frameworks-wordpress-security-validation"
  "toolchains-php-frameworks-wordpress-testing-qa"
  # Elixir
  "toolchains-elixir-data-ecto-patterns"
  "toolchains-elixir-frameworks-phoenix-api-channels"
  "toolchains-elixir-frameworks-phoenix-liveview"
  # Golang
  "toolchains-golang-cli"
  "toolchains-golang-data"
  "toolchains-golang-observability"
  "toolchains-golang-testing"
  "toolchains-golang-web"
  # Rust
  "toolchains-rust-desktop-applications"
  "toolchains-rust-frameworks-tauri"
  # UI/Frontend
  "toolchains-ui-components-daisyui"
  "toolchains-ui-components-headlessui"
  "toolchains-ui-components-shadcn"
  "toolchains-ui-styling-tailwind"
  # Platforms
  "toolchains-platforms-backend-supabase"
  "toolchains-platforms-database-neon"
  # AI services
  "toolchains-ai-services-openrouter"
  "toolchains-ai-techniques-session-compression"
  # GraphQL
  "toolchains-universal-data-graphql"
  # Examples
  "examples-bad-interdependent-skill"
  "examples-good-self-contained-skill"
  # Miscellaneous
  "universal-main-internal-comms"
  "universal-architecture-software-patterns"
  "universal-infrastructure-env-manager"
)

echo "Removing ${#REMOVE_SKILLS[@]} misaligned skills from $SKILLS_DIR"

for skill in "${REMOVE_SKILLS[@]}"; do
  if [ -d "$skill" ]; then
    echo "Removing: $skill"
    rm -rf "$skill"
  else
    echo "Skipping (not found): $skill"
  fi
done

echo "Cleanup complete!"
echo "Remaining skills:"
ls -1 | wc -l
```

## Impact Summary

### Before Cleanup
- **User-level skills**: 79 (ALL misaligned - global scope affecting all projects)
- **Project-level skills**: 91
- **Total skills**: 170

### After Cleanup
- **User-level skills**: 0 (removed)
- **Project-level skills**: ~37 (removed 54 misaligned skills)
- **Total skills**: ~37

### Skill Reduction
- **Removed**: ~133 skills (78% reduction)
- **Retained**: ~37 skills (22% - all aligned with agent capabilities)

## Skills Management Best Practices

### Metadata Files
Each skill contains a `metadata.json` file with:
- `name`: Skill identifier
- `version`: Semantic versioning
- `category`: toolchain/universal/main
- `tags`: Searchable keywords
- `entry_point_tokens`: Size of entry point
- `full_tokens`: Total skill size
- `related_skills`: Dependencies

### Safe Removal Process
1. **Backup**: `mv ~/.claude/skills ~/.claude/skills.backup-$(date +%Y-%m-%d)`
2. **Remove**: `rm -rf [skill-directory]`
3. **Verify**: Claude Code will detect missing skills on next startup
4. **No rollback needed**: Skills are stateless, can be re-deployed anytime

### Project vs User Skills
- **User skills** (`~/.claude/skills/`): Apply globally to all projects
- **Project skills** (`.claude/skills/`): Apply only to current project
- **Recommendation**: Use project-level skills for better isolation and alignment

## Recommendations

1. ✅ **Remove ALL user-level skills** - Global skills pollute all projects with irrelevant context
2. ✅ **Remove 54 misaligned project skills** - Focus only on Python, AI/ML, testing, ops, and documentation
3. ✅ **Keep 37 aligned skills** - Maintain skills that match actual agent capabilities
4. ⚠️ **Monitor skill usage** - Track which skills are actually invoked during agent operations
5. 📋 **Document skill rationale** - Each retained skill should map to specific agent capabilities

## Next Steps

1. Execute user-level skills cleanup: `rm -rf ~/.claude/skills`
2. Execute project-level skills cleanup using consolidated script
3. Restart Claude Code to reload skills
4. Verify agent behavior with reduced skill set
5. Monitor for any missing capabilities or regressions

## Conclusion

The current skills system contains 78% irrelevant skills (133 out of 170) targeting technologies not used by Claude MPM. Removing these skills will:

- Reduce context pollution
- Improve agent focus and performance
- Eliminate confusion from irrelevant technology suggestions
- Align skills precisely with agent capabilities
- Reduce memory and processing overhead

All misaligned skills can be safely removed without impacting Claude MPM functionality, as they target technologies (JavaScript, TypeScript, PHP, Elixir, Golang, Rust, UI frameworks) not used in this Python-based AI agent project.
